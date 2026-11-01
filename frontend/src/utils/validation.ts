import { MAX_UPLOAD_SIZE_MB, MIN_TEXT_LENGTH, type InputOption } from "@/data/options"

/** Returns an error message if the file can't be used for this input type, otherwise null. */
export function validateFile(file: File, option: InputOption): string | null {
  const dot = file.name.lastIndexOf(".")
  const extension = dot === -1 ? "" : file.name.slice(dot).toLowerCase()
  if (!option.extensions.includes(extension)) {
    return `Unsupported file type. Supported formats: ${option.formatsLabel}.`
  }
  if (file.size === 0) {
    return "The selected file is empty."
  }
  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    return `File is too large. The maximum size is ${MAX_UPLOAD_SIZE_MB} MB.`
  }
  return null
}

export function validateText(text: string): string | null {
  if (text.trim().length < MIN_TEXT_LENGTH) {
    return `Add at least ${MIN_TEXT_LENGTH} characters to continue.`
  }
  return null
}
