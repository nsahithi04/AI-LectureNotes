import { useState } from "react"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import { closeForm, listResponses, type SavedForm } from "@/services/googleForms"
import { formatDate } from "@/utils/format"
import { resultsToCsv, summariseResults, type AnswerStatus, type ResultsSummary } from "@/utils/formResults"

const STATUS_LABEL: Record<AnswerStatus, string> = {
  correct: "Correct",
  wrong: "Wrong",
  needs_marking: "Not marked",
  marked: "Marked",
  unanswered: "No answer",
}

interface FormDetailsProps {
  form: SavedForm
  onChange: (form: SavedForm) => void
}

/** A created Google Form: its links, what the teacher still has to set in Google Forms, and the students' results. */
export default function FormDetails({ form, onChange }: FormDetailsProps) {
  const [results, setResults] = useState<ResultsSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [closing, setClosing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [openStudent, setOpenStudent] = useState<string | null>(null)

  const deadlinePassed = form.closesAt !== null && new Date(form.closesAt).getTime() <= Date.now()

  async function handleClose(automatic = false) {
    setClosing(true)
    setError(null)
    try {
      await closeForm(form.formId)
      onChange({ ...form, closed: true })
      setNotice(automatic ? "The deadline has passed, so the form has stopped accepting answers." : "The form has stopped accepting answers.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setClosing(false)
    }
  }

  async function handleResults() {
    setLoading(true)
    setError(null)
    try {
      setResults(summariseResults(form, await listResponses(form.formId)))
      if (deadlinePassed && !form.closed) await handleClose(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setLoading(false)
    }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(form.studentLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  function downloadCsv() {
    if (!results) return
    const url = URL.createObjectURL(new Blob([resultsToCsv(form, results)], { type: "text/csv" }))
    const link = document.createElement("a")
    link.href = url
    link.download = `${form.title} results.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="input-panel">
      <div className="quiz-form-heading">
        <strong>{form.title}</strong>
        {form.closed ? <Badge label="Closed" tone="danger" /> : <Badge label="Open" tone="success" />}
      </div>
      <p className="quiz-note">
        Created {formatDate(form.createdAt)} · {form.questions.length} question{form.questions.length === 1 ? "" : "s"}
        {form.closesAt && ` · Due ${formatDate(form.closesAt)}`}
      </p>

      <div className="quiz-field">
        <label htmlFor={`link-${form.formId}`}>Link for students</label>
        <input id={`link-${form.formId}`} type="text" readOnly value={form.studentLink} onFocus={(event) => event.target.select()} />
      </div>

      <div className="leave-note quiz-steps">
        <Icon name="settings" />
        <div>
          <strong>Optional steps in Google Forms</strong>, because Google doesn’t let apps change these settings:
          <ol>
            <li>To give each student the questions in a different order: Settings → Presentation → turn on “Shuffle question order”.</li>
            {form.showResults ? (
              <li>
                Students see their marks straight after submitting. To hide them until you’ve marked the Q&A answers:
                Settings → Quizzes → Release grades → “Later, after manual review”.
              </li>
            ) : (
              <li>
                Students only see “Your response has been recorded”. This form isn’t a Google quiz, so LectureAI marks
                the multiple choice answers in your results, and shows the ideal answer next to each Q&A answer.
              </li>
            )}
          </ol>
        </div>
      </div>

      <div className="quiz-actions">
        <a className="btn btn-secondary" href={form.editLink} target="_blank" rel="noreferrer">
          <Icon name="external" size={18} />
          <span>Open in Google Forms</span>
        </a>
        <Button variant="secondary" icon="copy" onClick={copyLink}>
          {copied ? "Copied" : "Copy student link"}
        </Button>
        {!form.closed && (
          <Button variant="secondary" disabled={closing} onClick={() => handleClose()}>
            {closing ? "Closing..." : "Stop accepting answers"}
          </Button>
        )}
        <Button icon="chart" disabled={loading} onClick={handleResults}>
          {loading ? "Getting results..." : results ? "Refresh results" : "Get results"}
        </Button>
      </div>

      {notice && <p className="quiz-note">{notice}</p>}
      {error && (
        <div className="failure-box submit-error" role="alert">
          <Icon name="error" />
          <div>
            <strong>Something went wrong with Google Forms</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {results && (
        <div className="quiz-results">
          {results.students.length === 0 ? (
            <p className="quiz-note">No students have submitted yet.</p>
          ) : (
            <>
              <div className="quiz-results-stats">
                <div>
                  <strong>{results.students.length}</strong>
                  <span>Submitted</span>
                </div>
                <div>
                  <strong>
                    {results.averageScore} / {results.maxScore}
                  </strong>
                  <span>Average score</span>
                </div>
                <div>
                  <strong>{results.lateCount}</strong>
                  <span>Late</span>
                </div>
                <Button variant="ghost" icon="download" onClick={downloadCsv}>
                  Download CSV
                </Button>
              </div>
              <table className="quiz-results-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Submitted</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {results.students.map((student) => (
                    <tr key={student.responseId}>
                      <td>
                        <button
                          type="button"
                          className="quiz-student"
                          aria-expanded={openStudent === student.responseId}
                          onClick={() => setOpenStudent(openStudent === student.responseId ? null : student.responseId)}
                        >
                          {student.name}
                        </button>
                        {openStudent === student.responseId && (
                          <ol className="quiz-student-answers">
                            {student.answers.map((answer, index) => (
                              <li key={index}>
                                <strong>{answer.question}</strong>
                                <span>{answer.answer || "—"}</span>
                                {answer.idealAnswer && <small>Ideal answer: {answer.idealAnswer}</small>}
                                <em className={`status-${answer.status}`}>{STATUS_LABEL[answer.status]}</em>
                              </li>
                            ))}
                          </ol>
                        )}
                      </td>
                      <td>
                        {formatDate(student.submittedAt)}
                        {student.late && <Badge label="Late" tone="danger" />}
                      </td>
                      <td>
                        {student.score} / {results.maxScore}
                        {student.unmarked > 0 && form.showResults && <small> · {student.unmarked} to mark</small>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  )
}
