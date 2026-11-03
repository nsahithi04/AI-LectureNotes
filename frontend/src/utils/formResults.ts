import type { FormResponse, SavedForm } from "@/services/googleForms"

export type AnswerStatus = "correct" | "wrong" | "needs_marking" | "marked" | "unanswered"

export interface StudentResult {
  responseId: string
  name: string
  submittedAt: string
  late: boolean
  score: number
  /** Q&A answers the teacher hasn't marked in Google Forms yet. */
  unmarked: number
  answers: { question: string; answer: string; status: AnswerStatus; score: number | null; idealAnswer: string | null }[]
}

export interface ResultsSummary {
  students: StudentResult[]
  maxScore: number
  averageScore: number | null
  lateCount: number
}

function firstText(response: FormResponse, questionId: string): string {
  return response.answers?.[questionId]?.textAnswers?.answers?.[0]?.value?.trim() ?? ""
}

/** Turn Google's raw responses into one row per student, newest last. */
export function summariseResults(form: SavedForm, responses: FormResponse[]): ResultsSummary {
  const deadline = form.closesAt ? new Date(form.closesAt).getTime() : null

  const students = responses
    .map((response): StudentResult => {
      const answers = form.questions.map((question) => {
        const answer = firstText(response, question.questionId)
        const grade = response.answers?.[question.questionId]?.grade
        const base = { question: question.question, answer }
        if (question.type === "short_answer") {
          // Google only adds a score to a Q&A answer once the teacher has marked it in a quiz.
          const status: AnswerStatus = !answer ? "unanswered" : grade?.score === undefined ? "needs_marking" : "marked"
          return { ...base, status, score: grade?.score ?? null, idealAnswer: question.answer ?? null }
        }
        // Plain forms have no Google grade, so compare with the correct option LectureAI saved.
        const correct = grade ? Boolean(grade.correct) : Boolean(answer) && answer === question.answer?.trim()
        const status: AnswerStatus = !answer ? "unanswered" : correct ? "correct" : "wrong"
        return { ...base, status, score: grade?.score ?? (correct ? 1 : 0), idealAnswer: null }
      })
      const submittedAt = response.lastSubmittedTime || response.createTime
      return {
        responseId: response.responseId,
        name: firstText(response, form.nameQuestionId) || "No name given",
        submittedAt,
        late: deadline !== null && new Date(submittedAt).getTime() > deadline,
        score: response.totalScore ?? answers.reduce((total, answer) => total + (answer.score ?? 0), 0),
        unmarked: answers.filter((answer) => answer.status === "needs_marking").length,
        answers,
      }
    })
    .sort((a, b) => a.submittedAt.localeCompare(b.submittedAt))

  const total = students.reduce((sum, student) => sum + student.score, 0)
  return {
    students,
    // Plain forms can't have their Q&A answers marked in Google, so only multiple choice counts.
    maxScore: form.showResults ? form.questions.length : form.questions.filter((q) => q.type === "multiple_choice").length,
    averageScore: students.length ? Math.round((total / students.length) * 10) / 10 : null,
    lateCount: students.filter((student) => student.late).length,
  }
}

/** Results as CSV, for opening in Excel or Google Sheets. */
export function resultsToCsv(form: SavedForm, summary: ResultsSummary): string {
  const cell = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`
  const header = ["Name", "Submitted", "Late", `Score (out of ${summary.maxScore})`, ...form.questions.map((q) => q.question)]
  const rows = summary.students.map((student) => [
    student.name,
    student.submittedAt,
    student.late ? "Yes" : "No",
    student.score,
    ...student.answers.map((answer) => answer.answer),
  ])
  return [header, ...rows].map((row) => row.map(cell).join(",")).join("\n")
}
