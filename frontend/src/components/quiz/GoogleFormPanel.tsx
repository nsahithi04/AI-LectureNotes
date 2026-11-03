import { useState } from "react"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import { createQuizForm, isGoogleFormsConfigured, type SavedForm } from "@/services/googleForms"
import type { Question } from "@/types/lecture"

interface GoogleFormPanelProps {
  title: string
  questions: Question[]
  onCreated: (form: SavedForm) => void
}

/** "YYYY-MM-DDTHH:MM" in local time, the format a datetime-local input uses. */
function localInputValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

/** Asks the teacher's choices, then sends the selected questions to a new Google Forms quiz. */
export default function GoogleFormPanel({ title, questions, onCreated }: GoogleFormPanelProps) {
  const [closesAt, setClosesAt] = useState("")
  const [showResults, setShowResults] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deadlineError = closesAt && new Date(closesAt).getTime() <= Date.now() ? "Choose a time in the future." : null

  async function handleCreate() {
    setCreating(true)
    setError(null)
    try {
      onCreated(
        await createQuizForm(`${title} quiz`, questions, {
          closesAt: closesAt ? new Date(closesAt).toISOString() : null,
          showResults,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="input-panel">
      <div className="quiz-form-heading">
        <strong>Share as a Google Form</strong>
      </div>
      <p className="quiz-note">
        Creates a quiz with the {questions.length} selected question{questions.length === 1 ? "" : "s"} in your Google
        account. Every student gets the same questions, with the options in a different order. Students enter their name,
        and multiple choice answers are marked automatically.
      </p>

      <div className="quiz-field">
        <label htmlFor="form-closes-at">Accept answers until (optional)</label>
        <input
          id="form-closes-at"
          type="datetime-local"
          min={localInputValue(new Date())}
          value={closesAt}
          onChange={(event) => setClosesAt(event.target.value)}
        />
        <small>
          The deadline appears on the form, and late answers are marked in your results. Google can’t close a form on a
          schedule, so it closes when you next get results after the deadline, or when you click “Stop accepting answers”.
        </small>
        {deadlineError && <p className="field-error">{deadlineError}</p>}
      </div>

      <div className="quiz-field">
        <span>After submitting, students see</span>
        <div className="quiz-types quiz-types-two" role="radiogroup" aria-label="What students see">
          {[
            { value: true, title: "Their marks", description: "As soon as they submit. You mark Q&A answers in Google Forms." },
            { value: false, title: "“Response submitted”", description: "No marks. LectureAI marks multiple choice, and shows ideal answers for Q&A." },
          ].map((choice) => (
            <button
              key={String(choice.value)}
              type="button"
              role="radio"
              aria-checked={showResults === choice.value}
              className={`quiz-type ${showResults === choice.value ? "selected" : ""}`}
              onClick={() => setShowResults(choice.value)}
            >
              <strong>{choice.title}</strong>
              <small>{choice.description}</small>
            </button>
          ))}
        </div>
      </div>

      {!isGoogleFormsConfigured() && (
        <p className="field-error">Google Forms isn’t set up yet. Add VITE_GOOGLE_CLIENT_ID to frontend/.env.</p>
      )}
      {error && (
        <div className="failure-box submit-error" role="alert">
          <Icon name="error" />
          <div>
            <strong>We couldn’t create the Google Form</strong>
            <span>{error}</span>
          </div>
        </div>
      )}
      <div className="quiz-actions">
        <Button
          icon="external"
          disabled={!questions.length || creating || !isGoogleFormsConfigured() || Boolean(deadlineError)}
          onClick={handleCreate}
        >
          {creating ? "Creating your Google Form..." : "Create Google Form"}
        </Button>
      </div>
    </div>
  )
}
