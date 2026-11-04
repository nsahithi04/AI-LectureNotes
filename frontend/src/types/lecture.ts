// Shapes of the data exchanged with the backend. Field names match the API's JSON (snake_case).

export type InputType = "video" | "audio" | "document" | "text"

export type NoteType = "detailed" | "short" | "important"

export type LectureStatus = "uploaded" | "processing" | "completed" | "failed"

/**
 * Notes are a list of blocks so the backend can describe structure
 * (topics, subtopics, body text, bullet lists) without sending HTML.
 */
export type NoteBlock =
  | { type: "heading"; level: 1 | 2; text: string }
  | { type: "paragraph"; text: string }
  | { type: "bullets"; items: string[] }

export interface LectureSource {
  filename: string | null
  file_size: number | null
  characters: number | null
}

export interface Lecture {
  id: string
  title: string
  input_type: InputType
  status: LectureStatus
  note_types: NoteType[]
  source: LectureSource
  notes: Record<NoteType, NoteBlock[] | null>
  /** Timestamped transcript, for video and audio. */
  transcript?: TranscriptSegment[]
  /** The text the notes were made from, for every source type. */
  source_text?: string
  error: string | null
  created_at: string
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface NoteDefinition {
  term: string
  meaning: string
}

export interface NoteSection {
  heading: string
  content: string
  key_points: string[]
  definitions: NoteDefinition[]
  examples: string[]
}

export interface GeneratedNotes {
  title: string
  overview: string
  learning_objectives: string[]
  sections: NoteSection[]
  important_concepts: string[]
  key_takeaways: string[]
  conclusion: string
}

/** The `data` part of the responses from the /api/{video,audio,document,text}/process endpoints. */
export interface ProcessData {
  source: {
    type: InputType
    /** The file extension without the dot, such as "pptx". Null for pasted text. */
    format: string | null
    filename: string | null
    size: number | null
    duration: number | null
    /** Pages of a PDF, or slides of a PowerPoint file. */
    pages: number | null
    characters: number
  }
  transcription: { language: string; text: string; segments: TranscriptSegment[] } | null
  text: string
  lecture_notes: GeneratedNotes
}

export type ProcessInput = { inputType: "text"; text: string } | { inputType: Exclude<InputType, "text">; file: File }

export interface NewLectureInput {
  inputType: InputType
  noteTypes: NoteType[]
  file: File | null
  text: string
}

export type QuestionKind = "multiple_choice" | "short_answer"

export type QuestionChoice = QuestionKind | "both"

export interface Question {
  type: QuestionKind
  topic: string
  question: string
  options: string[]
  answer: string
}

export interface QuestionRequest {
  transcript: string
  count: number
  question_type: QuestionChoice
  instructions: string | null
}
