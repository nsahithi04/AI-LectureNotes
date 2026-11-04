import Badge from "@/components/ui/Badge"
import Icon from "@/components/ui/Icon"
import type { InputType } from "@/types/lecture"

const STEPS: Record<InputType, string> = {
  video: "We’re extracting the audio, transcribing the lecture and writing your notes.",
  audio: "We’re transcribing the recording and writing your notes.",
  document: "We’re reading the document and writing your notes.",
  text: "We’re writing your notes from the text.",
}

interface GeneratingViewProps {
  inputType: InputType
  name: string
  detail: string
}

/** Shown while the one long request runs. The backend reports no stages, so none are shown here. */
export default function GeneratingView({ inputType, name, detail }: GeneratingViewProps) {
  return (
    <div className="processing-card" role="status">
      <div className="processing-symbol">
        <Icon name="spark" size={32} />
      </div>
      <span className="eyebrow">AI PROCESSING</span>
      <h1>Generating your notes</h1>
      <p>{STEPS[inputType]} This can take a few minutes.</p>
      <div className="job-summary">
        <div className="file-large">
          <Icon name={inputType} />
        </div>
        <div>
          <strong>{name}</strong>
          <span>{detail}</span>
        </div>
        <Badge label="Processing" tone="info" />
      </div>
      <div className="leave-note">
        <Icon name="clock" />
        <span>Keep this page open. Your notes will appear here as soon as they’re ready.</span>
      </div>
    </div>
  )
}
