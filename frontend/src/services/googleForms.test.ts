import { afterEach, describe, expect, it, vi } from "vitest"
import type { Question } from "@/types/lecture"
import {
  GoogleFormsError,
  NAME_QUESTION,
  buildFormRequests,
  createQuizFormWithToken,
  formDescription,
  listResponsesWithToken,
} from "./googleForms"

const mcq: Question = {
  type: "multiple_choice",
  topic: "Overfitting",
  question: "What is overfitting?",
  options: ["Memorising data", "Sleeping"],
  answer: "Memorising data",
}
const short: Question = { type: "short_answer", topic: "Data", question: "Why split data?", options: [], answer: "To test." }
const NO_DEADLINE = { closesAt: null, showResults: true }
const WITH_DEADLINE = { closesAt: "2026-12-01T09:30:00.000Z", showResults: false }

type Request = Record<string, any>

describe("buildFormRequests", () => {
  const requests = buildFormRequests("Quiz", [mcq, short], NO_DEADLINE) as Request[]
  const items = requests.slice(1).map((request) => request.createItem)

  it("turns the form into a quiz first", () => {
    expect(requests[0].updateSettings.settings.quizSettings.isQuiz).toBe(true)
    expect(requests[0].updateSettings.updateMask).toBe("quizSettings.isQuiz")
  })

  it("asks for the student's name before the questions", () => {
    expect(items[0].item.title).toBe(NAME_QUESTION)
    expect(items[0].item.questionItem.question.grading).toBeUndefined()
  })

  it("adds questions in order", () => {
    expect(items.map((item) => item.location.index)).toEqual([0, 1, 2])
    expect(items.map((item) => item.item.title)).toEqual([NAME_QUESTION, "What is overfitting?", "Why split data?"])
  })

  it("marks multiple choice questions with the correct option", () => {
    const question = items[1].item.questionItem.question

    expect(question.choiceQuestion.type).toBe("RADIO")
    expect(question.choiceQuestion.options).toEqual([{ value: "Memorising data" }, { value: "Sleeping" }])
    expect(question.grading.correctAnswers.answers).toEqual([{ value: "Memorising data" }])
  })

  it("gives short answers the ideal answer as feedback", () => {
    const question = items[2].item.questionItem.question

    expect(question.textQuestion).toEqual({ paragraph: true })
    expect(question.grading.generalFeedback.text).toBe("Ideal answer: To test.")
    // Google rejects an answer key on paragraph questions.
    expect(question.grading.correctAnswers).toBeUndefined()
  })

  it("makes a plain form with no answer key when students shouldn't see marks", () => {
    const plain = buildFormRequests("Quiz", [mcq, short], WITH_DEADLINE) as Request[]
    const questions = plain.filter((request) => request.createItem).map((request) => request.createItem.item.questionItem.question)

    expect(plain.some((request) => request.updateSettings)).toBe(false)
    expect(questions.every((question) => question.grading === undefined)).toBe(true)
    expect(questions[1].choiceQuestion.shuffle).toBe(true)
  })

  it("adds the deadline to the form's description only when there is one", () => {
    expect(requests.some((request) => request.updateFormInfo)).toBe(false)

    const withDeadline = buildFormRequests("Quiz", [mcq], WITH_DEADLINE) as Request[]

    expect(withDeadline[0].updateFormInfo.updateMask).toBe("description")
    expect(withDeadline[0].updateFormInfo.info.description).toBe(formDescription(WITH_DEADLINE.closesAt))
    expect(formDescription(WITH_DEADLINE.closesAt)).toContain("Please submit by")
  })
})

describe("Google Forms requests", () => {
  afterEach(() => vi.unstubAllGlobals())

  function stubFetch(...replies: [number, object][]) {
    const calls: { url: string; method: string; body: Request | null; auth: string }[] = []
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init: RequestInit) => {
        calls.push({
          url,
          method: init.method ?? "GET",
          body: init.body ? JSON.parse(String(init.body)) : null,
          auth: new Headers(init.headers).get("Authorization") ?? "",
        })
        const [status, body] = replies.shift()!
        return new Response(JSON.stringify(body), { status })
      }),
    )
    return calls
  }

  // Google replies to each batchUpdate request in order, with an empty reply for settings and info changes.
  function batchReply(extraReplies: number, questionIds: string[], publishSettings?: object) {
    return {
      form: { formId: "abc", responderUri: "https://forms.example/student", publishSettings },
      replies: [...Array(extraReplies).fill({}), ...questionIds.map((id) => ({ createItem: { questionId: [id] } }))],
    }
  }

  it("creates, fills and publishes the form, and remembers its question IDs", async () => {
    const calls = stubFetch([200, { formId: "abc" }], [200, batchReply(1, ["q-name", "q-1"])], [200, {}])

    const form = await createQuizFormWithToken("token", "Week 3 quiz", [mcq], WITH_DEADLINE)

    expect(calls[0].body).toEqual({ info: { title: "Week 3 quiz", documentTitle: "Week 3 quiz" } })
    expect(calls[0].auth).toBe("Bearer token")
    expect(calls[1].url).toContain("/forms/abc:batchUpdate")
    expect(calls[2].url).toContain("/forms/abc:setPublishSettings")
    expect(calls[2].body!.publishSettings.publishState).toEqual({ isPublished: true, isAcceptingResponses: true })
    expect(form).toMatchObject({
      formId: "abc",
      studentLink: "https://forms.example/student",
      editLink: "https://docs.google.com/forms/d/abc/edit",
      closesAt: WITH_DEADLINE.closesAt,
      showResults: false,
      nameQuestionId: "q-name",
      questions: [{ questionId: "q-1", question: "What is overfitting?", type: "multiple_choice", answer: "Memorising data" }],
      closed: false,
    })
  })

  it("skips publishing when the form already accepts responses", async () => {
    const published = { publishState: { isPublished: true, isAcceptingResponses: true } }
    const calls = stubFetch([200, { formId: "abc" }], [200, batchReply(1, ["q-name", "q-1"], published)])

    await createQuizFormWithToken("token", "Quiz", [mcq], NO_DEADLINE)

    expect(calls).toHaveLength(2)
  })

  it("fails clearly if Google doesn't return the question IDs", async () => {
    stubFetch([200, { formId: "abc" }], [200, batchReply(1, ["q-name"])])

    await expect(createQuizFormWithToken("token", "Quiz", [mcq], NO_DEADLINE)).rejects.toThrow(/question IDs/)
  })

  it("explains when the Forms API isn't turned on", async () => {
    stubFetch([403, { error: { message: "Google Forms API has not been used in project 123 before or it is disabled." } }])

    await expect(createQuizFormWithToken("token", "Quiz", [mcq], NO_DEADLINE)).rejects.toThrow(/isn't turned on/)
  })

  it("passes on Google's reason when it rejects a request", async () => {
    stubFetch([200, { formId: "abc" }], [400, { error: { message: "Invalid option" } }])

    const error = await createQuizFormWithToken("token", "Quiz", [mcq], NO_DEADLINE).catch((err) => err)

    expect(error).toBeInstanceOf(GoogleFormsError)
    expect(error.message).toBe("Google Forms rejected the request: Invalid option")
  })

  it("reads every page of responses", async () => {
    const calls = stubFetch(
      [200, { responses: [{ responseId: "r1" }], nextPageToken: "next" }],
      [200, { responses: [{ responseId: "r2" }] }],
    )

    const responses = await listResponsesWithToken("token", "abc")

    expect(responses.map((response) => response.responseId)).toEqual(["r1", "r2"])
    expect(calls[0].method).toBe("GET")
    expect(calls[0].url).toMatch(/\/forms\/abc\/responses$/)
    expect(calls[1].url).toContain("/forms/abc/responses?pageToken=next")
  })

  it("explains when the form was deleted", async () => {
    stubFetch([404, { error: { message: "Requested entity was not found." } }])

    await expect(listResponsesWithToken("token", "abc")).rejects.toThrow(/may have been deleted/)
  })
})
