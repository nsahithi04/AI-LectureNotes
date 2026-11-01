import Icon from "@/components/ui/Icon"
import { INPUT_OPTIONS } from "@/data/options"
import type { InputType } from "@/types/lecture"

interface InputTypePickerProps {
  value: InputType
  onChange: (type: InputType) => void
}

export default function InputTypePicker({ value, onChange }: InputTypePickerProps) {
  return (
    <div className="input-type-grid" role="radiogroup" aria-label="Input type">
      {INPUT_OPTIONS.map((option) => {
        const selected = option.type === value
        return (
          <button
            key={option.type}
            type="button"
            role="radio"
            aria-checked={selected}
            className={`input-type-card ${selected ? "selected" : ""}`}
            disabled={option.soon}
            onClick={() => onChange(option.type)}
          >
            <div className="type-icon">
              <Icon name={option.type} />
            </div>
            <span>
              <strong>{option.title}</strong>
              <small>{option.description}</small>
            </span>
            {option.soon ? <small className="soon-tag">Soon</small> : <i className="radio">{selected && <b />}</i>}
            <em>{option.formatsLabel}</em>
          </button>
        )
      })}
    </div>
  )
}
