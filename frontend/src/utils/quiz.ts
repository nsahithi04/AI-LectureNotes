import type { Question } from "@/types/lecture"

/** A question while the teacher is reviewing it. `selected` questions go into the quiz. */
export interface QuizQuestion extends Question {
  id: number
  selected: boolean
}

export interface QuestionDraft {
  type: Question["type"]
  topic: string
  question: string
  options: string[]
  correctOption: number
  answer: string
}

export const EMPTY_DRAFT: QuestionDraft = {
  type: "multiple_choice",
  topic: "",
  question: "",
  options: ["", "", "", ""],
  correctOption: 0,
  answer: "",
}

export function toDraft(question: Question): QuestionDraft {
  const multipleChoice = question.type === "multiple_choice"
  return {
    type: question.type,
    topic: question.topic,
    question: question.question,
    options: multipleChoice ? question.options : EMPTY_DRAFT.options,
    correctOption: multipleChoice ? Math.max(question.options.indexOf(question.answer), 0) : 0,
    answer: multipleChoice ? "" : question.answer,
  }
}

/** Returns what's wrong with a draft, or null if it can be saved. */
export function validateDraft(draft: QuestionDraft): string | null {
  if (!draft.question.trim()) return "Write the question."
  if (draft.type === "short_answer") {
    return draft.answer.trim() ? null : "Write the ideal answer."
  }
  const options = draft.options.map((option) => option.trim())
  const filled = options.filter(Boolean)
  if (filled.length < 2) return "Add at least two options."
  if (new Set(filled).size !== filled.length) return "Each option must be different."
  if (!options[draft.correctOption]) return "Choose an option with text as the correct answer."
  return null
}

export function fromDraft(draft: QuestionDraft): Question {
  const common = { type: draft.type, topic: draft.topic.trim() || "Added by you", question: draft.question.trim() }
  if (draft.type === "short_answer") {
    return { ...common, options: [], answer: draft.answer.trim() }
  }
  return {
    ...common,
    options: draft.options.map((option) => option.trim()).filter(Boolean),
    answer: draft.options[draft.correctOption].trim(),
  }
}

/** Plain text of the questions with their answers, for copying. */
export function questionsToText(questions: Question[]): string {
  return questions
    .map((question, index) => {
      const lines = [`${index + 1}. ${question.question}`]
      question.options.forEach((option, i) => lines.push(`   ${String.fromCharCode(65 + i)}. ${option}`))
      lines.push(`   Answer: ${question.answer}`)
      return lines.join("\n")
    })
    .join("\n\n")
}
