// Shapes of the data exchanged with the backend. Field names match the API's JSON (snake_case).

export type InputType = "video" | "audio" | "text" | "pdf"

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
  transcript?: TranscriptSegment[]
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

/** The `data` part of the POST /api/video/process response. */
export interface VideoProcessData {
  video: { filename: string; duration: number; size: number }
  transcription: { language: string; text: string; segments: TranscriptSegment[] }
  lecture_notes: GeneratedNotes
}

export interface NewLectureInput {
  inputType: InputType
  noteTypes: NoteType[]
  file: File | null
  text: string
}
