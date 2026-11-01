import { useNavigate } from "react-router"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import type { InputType, Lecture } from "@/types/lecture"
import { formatFileSize } from "@/utils/format"

// The pipeline steps for each input type, after the upload itself.
function processingSteps(inputType: InputType): string[] {
  const extract: Record<InputType, string[]> = {
    video: ["Extract audio from video", "Transcribe speech to text"],
    audio: ["Transcribe speech to text"],
    pdf: ["Extract text from PDF"],
    text: [],
  }
  return ["Upload received", ...extract[inputType], "Generate notes"]
}

export default function ProcessingView({ lecture }: { lecture: Lecture }) {
  const navigate = useNavigate()
  const failed = lecture.status === "failed"
  const processing = lecture.status === "processing"
  const steps = processingSteps(lecture.input_type)

  return (
    <main className="page processing-page">
      <div className="processing-card">
        <div className={`processing-symbol ${failed ? "failed" : ""}`}>
          <Icon name={failed ? "error" : "spark"} size={32} />
        </div>
        <span className="eyebrow">{failed ? "PROCESSING FAILED" : processing ? "AI PROCESSING" : "WAITING TO PROCESS"}</span>
        <h1>
          {failed
            ? "We couldn’t finish this lecture"
            : processing
              ? "Generating your notes"
              : "Your lecture is uploaded"}
        </h1>
        <p>
          {failed
            ? "Your original upload is safe. Check the error below and try again."
            : "Your notes will appear here automatically as soon as they’re ready."}
        </p>
        <div className="job-summary">
          <div className="file-large">
            <Icon name={lecture.input_type} />
          </div>
          <div>
            <strong>{lecture.title}</strong>
            <span>
              {lecture.source.filename
                ? `${lecture.source.filename} · ${formatFileSize(lecture.source.file_size ?? 0)}`
                : `${(lecture.source.characters ?? 0).toLocaleString()} characters of text`}
            </span>
          </div>
          {failed ? <Badge label="Failed" tone="danger" /> : <Badge label={processing ? "Processing" : "Uploaded"} tone="info" />}
        </div>
        <div className="stepper">
          {steps.map((label, index) => {
            const state =
              index === 0 ? "complete" : failed && index === 1 ? "failed" : processing && index === 1 ? "current" : "pending"
            return (
              <div className={`step ${state}`} key={label}>
                <div className="step-dot">
                  {state === "complete" ? (
                    <Icon name="check" size={15} />
                  ) : state === "failed" ? (
                    <Icon name="error" size={15} />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <div>
                  <strong>{label}</strong>
                  <span>
                    {state === "complete"
                      ? "Completed"
                      : state === "current"
                        ? "In progress"
                        : state === "failed"
                          ? "Could not complete this step"
                          : "Waiting"}
                  </span>
                </div>
                {state === "current" && <i className="spinner" />}
              </div>
            )
          })}
        </div>
        {failed ? (
          <div className="failure-box">
            <Icon name="error" />
            <div>
              <strong>Processing error</strong>
              <span>{lecture.error ?? "Unknown error."}</span>
            </div>
          </div>
        ) : (
          <div className="leave-note">
            <Icon name="clock" />
            <span>
              {lecture.status === "uploaded"
                ? "Processing isn’t connected yet, so this lecture will stay at this step. See the README’s “Your tasks” section."
                : "You can safely leave this page and come back later."}
            </span>
          </div>
        )}
        <div className="processing-actions">
          <Button variant="secondary" icon="plus" onClick={() => navigate("/new")}>
            New lecture
          </Button>
          <Button variant="ghost" icon="eye" onClick={() => navigate("/preview")}>
            Preview sample notes
          </Button>
        </div>
      </div>
    </main>
  )
}
