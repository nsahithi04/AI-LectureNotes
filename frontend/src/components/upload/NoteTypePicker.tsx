import Icon from "@/components/ui/Icon"
import { NOTE_OPTIONS } from "@/data/options"
import type { NoteType } from "@/types/lecture"

interface NoteTypePickerProps {
  selected: NoteType[]
  onChange: (selected: NoteType[]) => void
}

export default function NoteTypePicker({ selected, onChange }: NoteTypePickerProps) {
  function toggle(type: NoteType) {
    onChange(selected.includes(type) ? selected.filter((t) => t !== type) : [...selected, type])
  }

  return (
    <div className="output-list">
      {NOTE_OPTIONS.map((option) => {
        const checked = selected.includes(option.type)
        return (
          <div className={`output-card ${checked ? "selected" : ""}`} key={option.type}>
            <button
              type="button"
              role="checkbox"
              aria-checked={checked}
              className="output-card-main"
              onClick={() => toggle(option.type)}
            >
              <span className="checkbox">{checked && <Icon name="check" size={15} />}</span>
              <span className="output-icon">
                <Icon name={option.icon} />
              </span>
              <span>
                <strong>
                  {option.title} {option.tag && <small>{option.tag}</small>}
                </strong>
                <em>{option.description}</em>
              </span>
            </button>
          </div>
        )
      })}
    </div>
  )
}
