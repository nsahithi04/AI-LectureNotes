import { useState } from "react"
import Button from "@/components/ui/Button"
import { MAX_INSTRUCTIONS_LENGTH, MAX_QUESTIONS, QUESTION_CHOICES } from "@/data/options"
import type { QuestionChoice } from "@/types/lecture"

export interface QuizSetup {
  count: number
  questionType: QuestionChoice
  instructions: string
}

interface QuizSetupFormProps {
  setup: QuizSetup
  onChange: (setup: QuizSetup) => void
  onGenerate: () => void
}

/** The teacher's choices before any questions are generated. */
export default function QuizSetupForm({ setup, onChange, onGenerate }: QuizSetupFormProps) {
  const [countText, setCountText] = useState(String(setup.count))
  const countValid = setup.count >= 1 && setup.count <= MAX_QUESTIONS && Number.isInteger(setup.count)

  return (
    <div className="input-panel">
      <div className="quiz-field">
        <label htmlFor="quiz-count">How many questions?</label>
        <input
          id="quiz-count"
          type="number"
          min={1}
          max={MAX_QUESTIONS}
          value={countText}
          onChange={(event) => {
            setCountText(event.target.value)
            onChange({ ...setup, count: Number(event.target.value) })
          }}
        />
        <small>Up to {MAX_QUESTIONS}. You can remove any you don’t want afterwards.</small>
        {!countValid && <p className="field-error">Enter a whole number from 1 to {MAX_QUESTIONS}.</p>}
      </div>

      <div className="quiz-field">
        <span>What type of questions?</span>
        <div className="quiz-types" role="radiogroup" aria-label="Question type">
          {QUESTION_CHOICES.map((choice) => {
            const selected = choice.type === setup.questionType
            return (
              <button
                key={choice.type}
                type="button"
                role="radio"
                aria-checked={selected}
                className={`quiz-type ${selected ? "selected" : ""}`}
                onClick={() => onChange({ ...setup, questionType: choice.type })}
              >
                <strong>{choice.title}</strong>
                <small>{choice.description}</small>
              </button>
            )
          })}
        </div>
      </div>

      <div className="quiz-field">
        <label htmlFor="quiz-instructions">Any additional requests? (optional)</label>
        <textarea
          id="quiz-instructions"
          maxLength={MAX_INSTRUCTIONS_LENGTH}
          placeholder="For example: more questions on gradient descent, and keep them beginner friendly."
          value={setup.instructions}
          onChange={(event) => onChange({ ...setup, instructions: event.target.value })}
        />
      </div>

      <div className="quiz-actions">
        <Button icon="spark" disabled={!countValid} onClick={onGenerate}>
          Generate Questions
        </Button>
      </div>
    </div>
  )
}
