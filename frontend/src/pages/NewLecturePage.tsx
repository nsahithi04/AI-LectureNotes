import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import GeneratingView from "@/components/lecture/GeneratingView"
import StepHeader from "@/components/layout/StepHeader"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import PageHeader from "@/components/ui/PageHeader"
import FileDropzone from "@/components/upload/FileDropzone"
import InputTypePicker from "@/components/upload/InputTypePicker"
import TextInputPanel from "@/components/upload/TextInputPanel"
import { getInputOption } from "@/data/options"
import { processLecture } from "@/services/api"
import type { InputType, ProcessInput } from "@/types/lecture"
import { formatFileSize } from "@/utils/format"
import { toLecture } from "@/utils/notes"
import { validateText } from "@/utils/validation"

/** Add a lecture (a file or text), then wait on this page while the backend turns it into notes. */
export default function NewLecturePage() {
  const navigate = useNavigate()
  const [inputType, setInputType] = useState<InputType>("video")
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState("")
  const [generating, setGenerating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const option = getInputOption(inputType)
  const isText = inputType === "text"
  const contentValid = isText ? validateText(text) === null : file !== null

  // The notes only reach this tab, so closing it mid-request would lose them.
  useEffect(() => {
    if (!generating) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [generating])

  function changeInputType(type: InputType) {
    setInputType(type)
    setFile(null)
    setSubmitError(null)
  }

  function changeFile(selected: File | null) {
    setFile(selected)
    setSubmitError(null)
  }

  async function handleGenerate() {
    let input: ProcessInput
    if (inputType === "text") input = { inputType, text: text.trim() }
    else if (file) input = { inputType, file }
    else return

    setGenerating(true)
    setSubmitError(null)
    try {
      const data = await processLecture(input)
      navigate("/notes", { state: { lecture: toLecture(data) } })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Something went wrong.")
      setGenerating(false)
    }
  }

  if (generating) {
    return (
      <div className="flow-page">
        <StepHeader step={2} title="Generate notes" />
        <main className="flow-content">
          <GeneratingView
            inputType={inputType}
            name={isText ? "Pasted lecture text" : (file?.name ?? "")}
            detail={isText ? `${text.trim().length.toLocaleString()} characters` : formatFileSize(file?.size ?? 0)}
          />
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
          subtitle="Upload a video, audio recording or document, or paste the lecture text, and get structured notes."
        />
        <InputTypePicker value={inputType} onChange={changeInputType} />
        {isText ? (
          <TextInputPanel value={text} onChange={setText} />
        ) : (
          <FileDropzone key={inputType} option={option} file={file} onFileChange={changeFile} />
        )}
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
            <span>{!contentValid && (isText ? "Add the lecture text to continue" : `Add a${inputType === "audio" ? "n" : ""} ${option.title.toLowerCase()} file to continue`)}</span>
            <Button icon="spark" disabled={!contentValid} onClick={handleGenerate}>
              Generate Lecture Notes
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
