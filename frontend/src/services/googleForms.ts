// Creates Google Forms quizzes in the teacher's own Google account and reads their responses,
// straight from the browser. The teacher signs in with a Google pop-up, and the token is only kept in memory.
import type { Question } from "@/types/lecture"

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ""
const SIGN_IN_SCRIPT = "https://accounts.google.com/gsi/client"
const FORMS_API = "https://forms.googleapis.com/v1/forms"
// Only gives access to files this app creates, not the rest of the teacher's Drive. It covers reading responses too.
const SCOPE = "https://www.googleapis.com/auth/drive.file"
// Ask Google again a little before the token runs out, rather than fail halfway through.
const TOKEN_MARGIN_MS = 60_000

export const NAME_QUESTION = "Your full name"

export class GoogleFormsError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "GoogleFormsError"
  }
}

export interface FormQuestion {
  questionId: string
  question: string
  type: Question["type"]
  /** The correct option, or the ideal answer. Older saved forms don't have it. */
  answer?: string
}

/** A form this app created. Kept in the browser, since there's no database yet. */
export interface SavedForm {
  formId: string
  title: string
  studentLink: string
  editLink: string
  createdAt: string
  /** When the teacher wants answers to stop, or null for no deadline. */
  closesAt: string | null
  /** Whether students see their marks after submitting. If not, the form isn't a Google quiz and LectureAI marks it. */
  showResults: boolean
  nameQuestionId: string
  questions: FormQuestion[]
  closed: boolean
}

export interface FormOptions {
  closesAt: string | null
  showResults: boolean
}

/** A student's submission, as Google returns it. */
export interface FormResponse {
  responseId: string
  createTime: string
  lastSubmittedTime: string
  totalScore?: number
  answers?: Record<string, { textAnswers?: { answers?: { value: string }[] }; grade?: { score?: number; correct?: boolean } }>
}

export function isGoogleFormsConfigured(): boolean {
  return GOOGLE_CLIENT_ID !== ""
}

// The parts of Google's sign-in library this file uses.
interface TokenResponse {
  access_token?: string
  expires_in?: number
  error?: string
}

interface GoogleSignIn {
  accounts: {
    oauth2: {
      initTokenClient(config: {
        client_id: string
        scope: string
        callback: (response: TokenResponse) => void
        error_callback: (error: { type: string }) => void
      }): { requestAccessToken(): void }
    }
  }
}

declare global {
  interface Window {
    google?: GoogleSignIn
  }
}

let scriptLoading: Promise<void> | null = null
let cachedToken: { value: string; expiresAt: number } | null = null

function loadSignInScript(): Promise<void> {
  if (window.google?.accounts) return Promise.resolve()
  scriptLoading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = SIGN_IN_SCRIPT
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      scriptLoading = null
      reject(new GoogleFormsError("Google sign-in couldn't load. Check your connection and try again."))
    }
    document.head.appendChild(script)
  })
  return scriptLoading
}

/** Returns a token, opening Google's sign-in pop-up if needed. Must be called from a click, or the browser blocks the pop-up. */
async function getAccessToken(): Promise<string> {
  if (!isGoogleFormsConfigured()) {
    throw new GoogleFormsError("Google Forms isn't set up yet. Add VITE_GOOGLE_CLIENT_ID to frontend/.env.")
  }
  if (cachedToken && cachedToken.expiresAt > Date.now()) return cachedToken.value

  await loadSignInScript()
  return new Promise((resolve, reject) => {
    const client = window.google!.accounts.oauth2.initTokenClient({
      client_id: GOOGLE_CLIENT_ID,
      scope: SCOPE,
      callback: (response) => {
        if (!response.access_token) {
          reject(new GoogleFormsError("Google didn't give permission to use Google Forms."))
          return
        }
        cachedToken = { value: response.access_token, expiresAt: Date.now() + (response.expires_in ?? 0) * 1000 - TOKEN_MARGIN_MS }
        resolve(response.access_token)
      },
      error_callback: (error) => {
        reject(
          new GoogleFormsError(
            error.type === "popup_failed_to_open"
              ? "The Google sign-in pop-up was blocked. Allow pop-ups for this site and try again."
              : "Google sign-in was closed before it finished.",
          ),
        )
      },
    })
    client.requestAccessToken()
  })
}

export function formDescription(closesAt: string | null): string {
  if (!closesAt) return ""
  const when = new Date(closesAt).toLocaleString(undefined, { dateStyle: "full", timeStyle: "short" })
  return `Please submit by ${when}. Answers after this time are marked as late.`
}

/**
 * The batchUpdate requests that turn an empty form into the quiz.
 *
 * Google shows quiz marks to students straight after they submit, and apps can't change that. So when the
 * teacher wants students to only see "Response submitted", the form is a plain form with no answer key,
 * and LectureAI marks the answers itself in the results.
 */
export function buildFormRequests(title: string, questions: Question[], options: FormOptions): object[] {
  const quiz = options.showResults
  const items = [
    // Personal Google accounts don't collect emails by default, so ask for a name to know who answered.
    { title: NAME_QUESTION, questionItem: { question: { required: true, textQuestion: { paragraph: false } } } },
    ...questions.map((question) => ({
      title: question.question,
      questionItem: {
        question:
          question.type === "multiple_choice"
            ? {
                required: true,
                ...(quiz && { grading: { pointValue: 1, correctAnswers: { answers: [{ value: question.answer }] } } }),
                choiceQuestion: { type: "RADIO", options: question.options.map((value) => ({ value })), shuffle: true },
              }
            : {
                required: true,
                // Google can't mark paragraph answers itself, so the teacher marks them in Google Forms.
                ...(quiz && { grading: { pointValue: 1, generalFeedback: { text: `Ideal answer: ${question.answer}` } } }),
                textQuestion: { paragraph: true },
              },
      },
    })),
  ]

  const description = formDescription(options.closesAt)
  return [
    ...(quiz ? [{ updateSettings: { settings: { quizSettings: { isQuiz: true } }, updateMask: "quizSettings.isQuiz" } }] : []),
    ...(description ? [{ updateFormInfo: { info: { title, description }, updateMask: "description" } }] : []),
    ...items.map((item, index) => ({ createItem: { item, location: { index } } })),
  ]
}

async function callForms<T>(token: string, path: string, body?: object): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${FORMS_API}${path}`, {
      method: body ? "POST" : "GET",
      headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new GoogleFormsError("Couldn't reach Google Forms. Check your connection and try again.")
  }

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail: string = data?.error?.message ?? ""
    if (response.status === 401) cachedToken = null
    if (response.status === 403 && /has not been used|is disabled/i.test(detail)) {
      throw new GoogleFormsError("The Google Forms API isn't turned on for this app's Google Cloud project.")
    }
    if (response.status === 404) {
      throw new GoogleFormsError("Google Forms couldn't find this form. It may have been deleted.")
    }
    if (response.status === 401 || response.status === 403) {
      throw new GoogleFormsError("Google didn't allow this. Sign in with the account that created the form, and accept the permission.")
    }
    if (response.status === 429) {
      throw new GoogleFormsError("Google Forms is receiving too many requests. Try again in a minute.")
    }
    throw new GoogleFormsError(detail ? `Google Forms rejected the request: ${detail}` : "Google Forms couldn't complete the request.")
  }
  return data as T
}

interface GoogleForm {
  formId: string
  responderUri?: string
  publishSettings?: { publishState?: { isPublished?: boolean; isAcceptingResponses?: boolean } }
}

interface BatchUpdateReply {
  form?: GoogleForm
  replies?: { createItem?: { questionId?: string[] } }[]
}

async function setAcceptingResponses(token: string, formId: string, accepting: boolean): Promise<void> {
  await callForms(token, `/${encodeURIComponent(formId)}:setPublishSettings`, {
    publishSettings: { publishState: { isPublished: true, isAcceptingResponses: accepting } },
    updateMask: "publishState",
  })
}

/** Create the quiz in the given account and publish it. Takes the token for testing. */
export async function createQuizFormWithToken(
  token: string,
  title: string,
  questions: Question[],
  options: FormOptions,
): Promise<SavedForm> {
  const created = await callForms<GoogleForm>(token, "", { info: { title, documentTitle: title } })
  const path = `/${encodeURIComponent(created.formId)}`
  const requests = buildFormRequests(title, questions, options)
  const updated = await callForms<BatchUpdateReply>(token, `${path}:batchUpdate`, { includeFormInResponse: true, requests })

  // Replies line up with requests. The items come last: the name question, then each quiz question.
  const itemReplies = (updated.replies ?? []).slice(requests.length - questions.length - 1)
  const questionIds = itemReplies.map((reply) => reply.createItem?.questionId?.[0] ?? "")
  if (questionIds.length !== questions.length + 1 || questionIds.some((id) => !id)) {
    throw new GoogleFormsError("The quiz was created, but Google didn't return its question IDs.")
  }

  const state = (updated.form ?? created).publishSettings?.publishState
  if (!state?.isPublished || !state.isAcceptingResponses) {
    await setAcceptingResponses(token, created.formId, true)
  }

  const studentLink = updated.form?.responderUri ?? created.responderUri
  if (!studentLink) throw new GoogleFormsError("The quiz was created, but Google didn't return its link.")

  return {
    formId: created.formId,
    title,
    studentLink,
    editLink: `https://docs.google.com/forms/d/${created.formId}/edit`,
    createdAt: new Date().toISOString(),
    closesAt: options.closesAt,
    showResults: options.showResults,
    nameQuestionId: questionIds[0],
    questions: questions.map((question, index) => ({
      questionId: questionIds[index + 1],
      question: question.question,
      type: question.type,
      answer: question.answer,
    })),
    closed: false,
  }
}

/** All responses to a form, following Google's pages. Takes the token for testing. */
export async function listResponsesWithToken(token: string, formId: string): Promise<FormResponse[]> {
  const responses: FormResponse[] = []
  let pageToken = ""
  do {
    const query = pageToken ? `?pageToken=${encodeURIComponent(pageToken)}` : ""
    const page = await callForms<{ responses?: FormResponse[]; nextPageToken?: string }>(
      token,
      `/${encodeURIComponent(formId)}/responses${query}`,
    )
    responses.push(...(page.responses ?? []))
    pageToken = page.nextPageToken ?? ""
  } while (pageToken)
  return responses
}

/** Sign the teacher in with Google, then create the quiz in their account. */
export async function createQuizForm(title: string, questions: Question[], options: FormOptions): Promise<SavedForm> {
  return createQuizFormWithToken(await getAccessToken(), title, questions, options)
}

export async function listResponses(formId: string): Promise<FormResponse[]> {
  return listResponsesWithToken(await getAccessToken(), formId)
}

/** Stop the form accepting answers. Google can't do this on a schedule, so it happens when the teacher asks. */
export async function closeForm(formId: string): Promise<void> {
  await setAcceptingResponses(await getAccessToken(), formId, false)
}
