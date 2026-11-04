// All communication with the FastAPI backend goes through this module.
import type { Lecture, NewLectureInput, ProcessData, ProcessInput, Question, QuestionRequest } from "@/types/lecture"

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "")

export class ApiError extends Error {
  status: number | null
  code: string | null

  constructor(message: string, status: number | null = null, code: string | null = null) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(`Could not reach the backend at ${API_BASE_URL}. Is it running?`)
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = body?.error?.message ?? `Request failed with status ${response.status}.`
    throw new ApiError(message, response.status, body?.error?.code ?? null)
  }
  if (body === null) {
    throw new ApiError("The backend returned an invalid response.", response.status)
  }
  return body as T
}

export function checkHealth(): Promise<{ status: string; message: string }> {
  return request("/api/health")
}

/** Upload a lecture (file or text) with the note types to generate. */
export function createLecture({ inputType, noteTypes, file, text }: NewLectureInput): Promise<Lecture> {
  const formData = new FormData()
  formData.append("input_type", inputType)
  noteTypes.forEach((noteType) => formData.append("note_types", noteType))
  if (inputType === "text") {
    formData.append("text", text)
  } else if (file) {
    formData.append("file", file)
  }
  // No Content-Type header: the browser sets it, including the multipart boundary.
  return request("/api/lectures", { method: "POST", body: formData })
}

/** Send a lecture through the whole pipeline. This one request lasts until the notes are ready. */
export async function processLecture(input: ProcessInput): Promise<ProcessData> {
  let init: RequestInit
  if (input.inputType === "text") {
    init = { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: input.text }) }
  } else {
    // The form field is named after the input type: video, audio or document.
    const formData = new FormData()
    formData.append(input.inputType, input.file)
    init = { method: "POST", body: formData }
  }
  const response = await request<{ data: ProcessData }>(`/api/${input.inputType}/process`, init)
  return response.data
}

/** Generate quiz questions from a lecture's transcript. */
export async function generateQuestions(input: QuestionRequest): Promise<Question[]> {
  const response = await request<{ data: { questions: Question[] } }>("/api/questions/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
  return response.data.questions
}

export function getLecture(lectureId: string): Promise<Lecture> {
  return request(`/api/lectures/${encodeURIComponent(lectureId)}`)
}

export function listLectures(): Promise<Lecture[]> {
  return request("/api/lectures")
}
