import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import GeneratingView from "@/components/lecture/GeneratingView"
import StepHeader from "@/components/layout/StepHeader"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import PageHeader from "@/components/ui/PageHeader"
import FileDropzone from "@/components/upload/FileDropzone"
import InputTypePicker from "@/components/upload/InputTypePicker"
import { getInputOption } from "@/data/options"
import { processVideo } from "@/services/api"
import { toLecture } from "@/utils/notes"

/** Add a video, then wait on this page while the backend turns it into notes. */
export default function NewLecturePage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [generating, setGenerating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const option = getInputOption("video")

  // The notes only reach this tab, so closing it mid-request would lose them.
  useEffect(() => {
    if (!generating) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [generating])

  function changeFile(selected: File | null) {
    setFile(selected)
    setSubmitError(null)
  }

  async function handleGenerate() {
    if (!file) return
    setGenerating(true)
    setSubmitError(null)
    try {
      const data = await processVideo(file)
      navigate("/notes", { state: { lecture: toLecture(data) } })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Something went wrong.")
      setGenerating(false)
    }
  }

  if (generating && file) {
    return (
      <div className="flow-page">
        <StepHeader step={2} title="Generate notes" />
        <main className="flow-content">
          <GeneratingView file={file} />
        </main>
      </div>
    )
  }

  return (
    <div className="flow-page">
      <StepHeader step={1} title="Add your content" />
      <main className="flow-content">
        <PageHeader
          eyebrow="NEW LECTURE"
          title="Add your lecture"
          subtitle="Upload a lecture video and get structured notes and a transcript."
        />
        <InputTypePicker value="video" onChange={() => undefined} />
        <FileDropzone option={option} file={file} onFileChange={changeFile} />
        <div className="ai-note">
          <Icon name="spark" size={17} />
          <span>AI-generated notes may contain errors. Check them against the lecture before relying on them.</span>
        </div>
        {submitError && (
          <div className="failure-box submit-error" role="alert">
            <Icon name="error" />
            <div>
              <strong>We couldn’t generate notes</strong>
              <span>{submitError}</span>
            </div>
          </div>
        )}
        <div className="flow-actions">
          <Button variant="secondary" onClick={() => navigate("/")}>
            Cancel
          </Button>
          <div>
            <span>{!file && "Add a video to continue"}</span>
            <Button icon="spark" disabled={!file} onClick={handleGenerate}>
              Generate Lecture Notes
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
