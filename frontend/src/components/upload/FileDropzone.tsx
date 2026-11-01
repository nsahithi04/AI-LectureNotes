import { useRef, useState, type DragEvent } from "react"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import { MAX_UPLOAD_SIZE_MB, type InputOption } from "@/data/options"
import { formatFileSize } from "@/utils/format"
import { validateFile } from "@/utils/validation"

interface FileDropzoneProps {
  option: InputOption
  file: File | null
  onFileChange: (file: File | null) => void
}

export default function FileDropzone({ option, file, onFileChange }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function selectFile(selected: File | undefined) {
    if (!selected) return
    const message = validateFile(selected, option)
    setError(message)
    onFileChange(message ? null : selected)
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files[0])
  }

  return (
    <div className="input-panel">
      <input
        ref={inputRef}
        type="file"
        accept={option.extensions.join(",")}
        hidden
        onChange={(event) => {
          selectFile(event.target.files?.[0])
          // Reset so choosing the same file again still triggers a change.
          event.target.value = ""
        }}
      />
      {file ? (
        <div className="selected-file">
          <div className="file-large">
            <Icon name={option.type} />
          </div>
          <div>
            <strong>{file.name}</strong>
            <span>
              {formatFileSize(file.size)} · {option.title}
            </span>
            <div className="file-ready">
              <Icon name="check" size={14} />
              Ready to upload
            </div>
          </div>
          <Button variant="ghost" onClick={() => onFileChange(null)}>
            Remove
          </Button>
        </div>
      ) : (
        <button
          type="button"
          className={`dropzone ${isDragging ? "dragging" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <span className="drop-icon">
            <Icon name="upload" size={26} />
          </span>
          <strong>Drag your {option.title.toLowerCase()} file here</strong>
          <span>
            or <u>browse files</u> from your computer
          </span>
          <small>
            {option.formatsLabel} · {option.maxMinutes && `Up to ${option.maxMinutes} minutes · `}Maximum file size {MAX_UPLOAD_SIZE_MB} MB
          </small>
        </button>
      )}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
