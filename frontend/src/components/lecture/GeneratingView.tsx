import Badge from "@/components/ui/Badge"
import Icon from "@/components/ui/Icon"
import { formatFileSize } from "@/utils/format"

/** Shown while the one long request runs. The backend reports no stages, so none are shown here. */
export default function GeneratingView({ file }: { file: File }) {
  return (
    <div className="processing-card" role="status">
      <div className="processing-symbol">
        <Icon name="spark" size={32} />
      </div>
      <span className="eyebrow">AI PROCESSING</span>
      <h1>Generating your notes</h1>
      <p>We’re extracting the audio, transcribing the lecture and writing your notes. This can take a few minutes.</p>
      <div className="job-summary">
        <div className="file-large">
          <Icon name="video" />
        </div>
        <div>
          <strong>{file.name}</strong>
          <span>{formatFileSize(file.size)}</span>
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
