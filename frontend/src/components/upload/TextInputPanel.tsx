import { MIN_TEXT_LENGTH } from "@/data/options"

interface TextInputPanelProps {
  value: string
  onChange: (text: string) => void
}

export default function TextInputPanel({ value, onChange }: TextInputPanelProps) {
  const tooShort = value.length > 0 && value.trim().length < MIN_TEXT_LENGTH
  return (
    <div className="input-panel">
      <div className="panel-label">
        <div>
          <label htmlFor="lectureText">Lecture content</label>
          <span>Paste a transcript, notes, or educational content below.</span>
        </div>
        {value && (
          <button type="button" onClick={() => onChange("")}>
            Clear text
          </button>
        )}
      </div>
      <textarea
        id="lectureText"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Paste your lecture transcript or educational content here..."
      />
      <div className="character-count">
        <span>{tooShort ? `Add at least ${MIN_TEXT_LENGTH} characters to continue` : "Your text stays private to this lecture."}</span>
        <span>{value.length.toLocaleString()} characters</span>
      </div>
    </div>
  )
}
