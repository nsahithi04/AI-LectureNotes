import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import type { QuizQuestion } from "@/utils/quiz"

interface QuestionCardProps {
  question: QuizQuestion
  number: number
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}

export default function QuestionCard({ question, number, onToggle, onEdit, onDelete }: QuestionCardProps) {
  return (
    <div className={`quiz-question ${question.selected ? "" : "unselected"}`}>
      <input type="checkbox" aria-label={`Include question ${number}`} checked={question.selected} onChange={onToggle} />
      <div className="quiz-question-body">
        <div className="quiz-meta">
          <Badge label={question.type === "multiple_choice" ? "Multiple choice" : "Q&A"} tone="info" />
          <span>{question.topic}</span>
        </div>
        <p>
          {number}. {question.question}
        </p>
        {question.type === "multiple_choice" ? (
          <ul className="quiz-options">
            {question.options.map((option) => (
              <li className={option === question.answer ? "correct" : ""} key={option}>
                {option === question.answer && <Icon name="check" size={13} />}
                {option}
              </li>
            ))}
          </ul>
        ) : (
          <div className="quiz-answer">
            <strong>Ideal answer:</strong> {question.answer}
          </div>
        )}
        <div className="quiz-question-actions">
          <Button variant="ghost" icon="edit" onClick={onEdit}>
            Edit
          </Button>
          <Button variant="ghost" icon="trash" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}
