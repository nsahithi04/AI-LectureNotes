import { describe, expect, it } from "vitest"
import type { Question } from "@/types/lecture"
import { EMPTY_DRAFT, fromDraft, questionsToText, toDraft, validateDraft } from "./quiz"

const mcq: Question = {
  type: "multiple_choice",
  topic: "Overfitting",
  question: "What is overfitting?",
  options: ["Memorising data", "Sleeping", "Cooking", "Running"],
  answer: "Memorising data",
}
const short: Question = { type: "short_answer", topic: "Data", question: "Why split data?", options: [], answer: "To test." }

describe("validateDraft", () => {
  it("accepts complete questions", () => {
    expect(validateDraft(toDraft(mcq))).toBeNull()
    expect(validateDraft(toDraft(short))).toBeNull()
  })

  it("needs a question", () => {
    expect(validateDraft({ ...toDraft(mcq), question: "  " })).toBe("Write the question.")
  })

  it("needs an ideal answer for Q&A", () => {
    expect(validateDraft({ ...toDraft(short), answer: "" })).toBe("Write the ideal answer.")
  })

  it("needs two different options and a correct one with text", () => {
    const draft = { ...EMPTY_DRAFT, question: "Q?" }

    expect(validateDraft({ ...draft, options: ["A", "", "", ""] })).toBe("Add at least two options.")
    expect(validateDraft({ ...draft, options: ["A", "A", "", ""] })).toBe("Each option must be different.")
    expect(validateDraft({ ...draft, options: ["A", "B", "", ""], correctOption: 2 })).toContain("correct answer")
  })
})

describe("drafts", () => {
  it("keep a question unchanged when no edits are made", () => {
    expect(fromDraft(toDraft(mcq))).toEqual(mcq)
    expect(fromDraft(toDraft(short))).toEqual(short)
  })

  it("drop blank options and keep the chosen answer", () => {
    const question = fromDraft({ ...EMPTY_DRAFT, question: "Q?", options: ["A", "", "C", ""], correctOption: 2 })

    expect(question.options).toEqual(["A", "C"])
    expect(question.answer).toBe("C")
    expect(question.topic).toBe("Added by you")
  })
})

it("questionsToText numbers questions and shows answers", () => {
  const text = questionsToText([mcq, short])

  expect(text).toContain("1. What is overfitting?\n   A. Memorising data")
  expect(text).toContain("   Answer: Memorising data")
  expect(text).toContain("2. Why split data?\n   Answer: To test.")
})
