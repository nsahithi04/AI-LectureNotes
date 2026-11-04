import type { IconName } from "@/components/ui/Icon"
import type { InputType, NoteType, QuestionChoice } from "@/types/lecture"

export interface InputOption {
  type: InputType
  title: string
  description: string
  formatsLabel: string
  /** File extensions accepted for upload; empty for pasted text. */
  extensions: string[]
  /** Longest recording the backend accepts; keep in sync with its MAX_VIDEO_MINUTES and MAX_AUDIO_MINUTES. */
  maxMinutes?: number
  /** Shown but can't be selected yet. */
  soon?: boolean
}

export const INPUT_OPTIONS: InputOption[] = [
  { type: "video", title: "Video", description: "Upload a recorded lecture", formatsLabel: "MP4, MOV, MKV", extensions: [".mp4", ".mov", ".mkv"], maxMinutes: 15 },
  { type: "audio", title: "Audio", description: "Upload an audio recording", formatsLabel: "MP3, WAV, M4A", extensions: [".mp3", ".wav", ".m4a"], maxMinutes: 30 },
  {
    type: "document",
    title: "Document",
    description: "Upload slides, handouts or notes",
    formatsLabel: "PDF, Word, PowerPoint",
    extensions: [".pdf", ".docx", ".pptx"],
  },
  { type: "text", title: "Text", description: "Paste a transcript or lecture text", formatsLabel: "Plain text", extensions: [] },
]

export interface NoteOption {
  type: NoteType
  title: string
  description: string
  icon: IconName
  tag?: string
}

export const NOTE_OPTIONS: NoteOption[] = [
  {
    type: "detailed",
    title: "Detailed notes",
    description: "The full lecture, organized into topics, subtopics and body text.",
    icon: "text",
  },
  {
    type: "short",
    title: "Short notes",
    description: "Only the main points of each topic, for revision.",
    icon: "note",
    tag: "Revision",
  },
  {
    type: "important",
    title: "Important points",
    description: "The key takeaways in a short list you can skim in a minute.",
    icon: "spark",
  },
]

export const TRANSCRIPT_OPTION = {
  title: "Transcript",
  description: "Everything said in the lecture, with timestamps.",
  icon: "audio",
} as const

export const SOURCE_TEXT_OPTION = {
  title: "Source text",
  description: "The text the notes were made from.",
  icon: "text",
} as const

export const QUIZ_OPTION = {
  title: "Quiz",
  description: "Choose the questions to give your students.",
  icon: "question",
} as const

export const QUESTION_CHOICES: { type: QuestionChoice; title: string; description: string }[] = [
  { type: "multiple_choice", title: "Multiple choice", description: "Four options, one correct" },
  { type: "short_answer", title: "Q&A", description: "Written answers, with an ideal answer" },
  { type: "both", title: "Both", description: "A mix of the two" },
]

export const MAX_QUESTIONS = 50
export const MAX_INSTRUCTIONS_LENGTH = 1000

export const MIN_TEXT_LENGTH = 30
export const MAX_UPLOAD_SIZE_MB = Number(import.meta.env.VITE_MAX_UPLOAD_SIZE_MB) || 500

export function getInputOption(type: InputType): InputOption {
  return INPUT_OPTIONS.find((option) => option.type === type)!
}

export function getNoteOption(type: NoteType): NoteOption {
  return NOTE_OPTIONS.find((option) => option.type === type)!
}
