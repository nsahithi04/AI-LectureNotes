import { describe, expect, it } from "vitest"
import type { FormResponse, SavedForm } from "@/services/googleForms"
import { resultsToCsv, summariseResults } from "./formResults"

const form: SavedForm = {
  formId: "abc",
  title: "Week 3 quiz",
  studentLink: "https://forms.example/student",
  editLink: "https://docs.google.com/forms/d/abc/edit",
  createdAt: "2026-11-01T09:00:00Z",
  closesAt: "2026-11-02T09:00:00Z",
  showResults: true,
  nameQuestionId: "name",
  questions: [
    { questionId: "q1", question: "What is overfitting?", type: "multiple_choice" },
    { questionId: "q2", question: "Why split data?", type: "short_answer" },
  ],
  closed: false,
}

function text(value: string) {
  return { textAnswers: { answers: [{ value }] } }
}

const onTime: FormResponse = {
  responseId: "r1",
  createTime: "2026-11-01T10:00:00Z",
  lastSubmittedTime: "2026-11-01T10:00:00Z",
  totalScore: 2,
  answers: {
    name: text("Asha"),
    q1: { ...text("Memorising data"), grade: { score: 1, correct: true } },
    q2: { ...text("To test the model."), grade: { score: 1 } },
  },
}

const late: FormResponse = {
  responseId: "r2",
  createTime: "2026-11-02T10:00:00Z",
  lastSubmittedTime: "2026-11-02T10:00:00Z",
  answers: {
    name: text("Ravi"),
    q1: { ...text("Sleeping"), grade: { score: 0, correct: false } },
    q2: text("No idea"),
  },
}

describe("summariseResults", () => {
  const summary = summariseResults(form, [late, onTime])

  it("lists students in the order they submitted", () => {
    expect(summary.students.map((student) => student.name)).toEqual(["Asha", "Ravi"])
  })

  it("marks submissions after the deadline as late", () => {
    expect(summary.students.map((student) => student.late)).toEqual([false, true])
    expect(summary.lateCount).toBe(1)
  })

  it("uses Google's total score, or adds up the answers when it's missing", () => {
    expect(summary.students.map((student) => student.score)).toEqual([2, 0])
    expect(summary.maxScore).toBe(2)
    expect(summary.averageScore).toBe(1)
  })

  it("shows which Q&A answers still need marking", () => {
    const [asha, ravi] = summary.students

    expect(asha.answers.map((answer) => answer.status)).toEqual(["correct", "marked"])
    expect(ravi.answers.map((answer) => answer.status)).toEqual(["wrong", "needs_marking"])
    expect(ravi.unmarked).toBe(1)
  })

  it("handles a form with no deadline and missing answers", () => {
    const result = summariseResults({ ...form, closesAt: null }, [{ ...late, answers: {} }])

    expect(result.students[0]).toMatchObject({ name: "No name given", late: false, score: 0 })
    expect(result.students[0].answers.every((answer) => answer.status === "unanswered")).toBe(true)
  })

  it("has no average when nobody has submitted", () => {
    expect(summariseResults(form, []).averageScore).toBeNull()
  })
})

describe("plain forms, where students only see \"Response submitted\"", () => {
  const plain: SavedForm = {
    ...form,
    showResults: false,
    questions: [
      { ...form.questions[0], answer: "Memorising data" },
      { ...form.questions[1], answer: "To check the model on new data." },
    ],
  }
  const ungraded = (value: string): FormResponse => ({
    ...onTime,
    totalScore: undefined,
    answers: { name: text("Asha"), q1: text(value), q2: text("To test.") },
  })

  it("marks multiple choice against the saved correct option", () => {
    expect(summariseResults(plain, [ungraded("Memorising data")]).students[0].answers[0]).toMatchObject({ status: "correct", score: 1 })
    expect(summariseResults(plain, [ungraded("Sleeping")]).students[0].answers[0]).toMatchObject({ status: "wrong", score: 0 })
  })

  it("scores out of the multiple choice questions only, and shows ideal answers for Q&A", () => {
    const summary = summariseResults(plain, [ungraded("Memorising data")])

    expect(summary.maxScore).toBe(1)
    expect(summary.students[0].score).toBe(1)
    expect(summary.students[0].answers[1].idealAnswer).toBe("To check the model on new data.")
  })
})

it("resultsToCsv has one row per student and escapes quotes", () => {
  const csv = resultsToCsv(form, summariseResults(form, [{ ...onTime, answers: { ...onTime.answers, name: text('Asha "A"') } }]))
  const lines = csv.split("\n")

  expect(lines[0]).toBe('"Name","Submitted","Late","Score (out of 2)","What is overfitting?","Why split data?"')
  expect(lines[1]).toContain('"Asha ""A"""')
  expect(lines).toHaveLength(2)
})
