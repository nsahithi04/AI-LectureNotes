import { useState } from "react"
import Button from "@/components/ui/Button"
import type { Question, QuestionKind } from "@/types/lecture"
import { EMPTY_DRAFT, fromDraft, toDraft, validateDraft } from "@/utils/quiz"

interface QuestionEditorProps {
  question?: Question
  onSave: (question: Question) => void
  onCancel: () => void
}

/** Add a new question, or edit an existing one. */
export default function QuestionEditor({ question, onSave, onCancel }: QuestionEditorProps) {
  const [draft, setDraft] = useState(question ? toDraft(question) : EMPTY_DRAFT)
  const [error, setError] = useState<string | null>(null)

  function save() {
    const message = validateDraft(draft)
    setError(message)
    if (!message) onSave(fromDraft(draft))
  }

  function changeOption(index: number, value: string) {
    setDraft({ ...draft, options: draft.options.map((option, i) => (i === index ? value : option)) })
  }

  return (
    <div className="input-panel">
      <div className="quiz-field">
        <label htmlFor="question-type">Type</label>
        <select
          id="question-type"
          value={draft.type}
          onChange={(event) => setDraft({ ...draft, type: event.target.value as QuestionKind })}
        >
          <option value="multiple_choice">Multiple choice</option>
          <option value="short_answer">Q&A</option>
        </select>
      </div>
      <div className="quiz-field">
        <label htmlFor="question-text">Question</label>
        <textarea
          id="question-text"
          value={draft.question}
          onChange={(event) => setDraft({ ...draft, question: event.target.value })}
        />
      </div>
      {draft.type === "multiple_choice" ? (
        <div className="quiz-field">
          <span>Options</span>
          <small>Select the correct answer.</small>
          {draft.options.map((option, index) => (
            <div className="quiz-option-row" key={index}>
              <input
                type="radio"
                name="correct-option"
                aria-label={`Option ${index + 1} is correct`}
                checked={draft.correctOption === index}
                onChange={() => setDraft({ ...draft, correctOption: index })}
              />
              <input
                type="text"
                aria-label={`Option ${index + 1}`}
                value={option}
                onChange={(event) => changeOption(index, event.target.value)}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="quiz-field">
          <label htmlFor="question-answer">Ideal answer</label>
          <textarea
            id="question-answer"
            value={draft.answer}
            onChange={(event) => setDraft({ ...draft, answer: event.target.value })}
          />
        </div>
      )}
      <div className="quiz-field">
        <label htmlFor="question-topic">Topic (optional)</label>
        <input
          id="question-topic"
          type="text"
          value={draft.topic}
          onChange={(event) => setDraft({ ...draft, topic: event.target.value })}
        />
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <div className="quiz-actions">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button icon="check" onClick={save}>
          Save question
        </Button>
      </div>
    </div>
  )
}
