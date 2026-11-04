import { describe, expect, it } from "vitest"
import type { GeneratedNotes, NoteBlock, ProcessData } from "@/types/lecture"
import { formatTimestamp, textToBlocks, transcriptToText } from "./format"
import { toLecture } from "./notes"

const notes: GeneratedNotes = {
  title: "Machine Learning",
  overview: "An introduction.",
  learning_objectives: ["Explain overfitting"],
  sections: [
    {
      heading: "Overfitting",
      content: "When a model memorises its training data.",
      key_points: ["Use a validation set"],
      definitions: [{ term: "Validation set", meaning: "Data held back for checking a model" }],
      examples: ["A model that scores 100% in training"],
    },
  ],
  important_concepts: ["Generalization"],
  key_takeaways: ["Test on unseen data"],
  conclusion: "Models must generalize.",
}

function response(overrides: Partial<GeneratedNotes> = {}): ProcessData {
  return {
    source: { type: "video", format: "mp4", filename: "lecture.mp4", size: 1024, duration: 60, pages: null, characters: 6 },
    transcription: { language: "en", text: "Hello.", segments: [{ start: 0, end: 1, text: "Hello." }] },
    text: "Hello.",
    lecture_notes: { ...notes, ...overrides },
  }
}

function text(blocks: NoteBlock[] | null): string {
  return JSON.stringify(blocks)
}

describe("toLecture", () => {
  it("keeps the title, source and transcript", () => {
    const lecture = toLecture(response())

    expect(lecture.title).toBe("Machine Learning")
    expect(lecture.status).toBe("completed")
    expect(lecture.source.filename).toBe("lecture.mp4")
    expect(lecture.source.file_size).toBe(1024)
    expect(lecture.transcript).toHaveLength(1)
  })

  it("keeps the text of a document or pasted text, without a transcript", () => {
    const lecture = toLecture({
      ...response(),
      source: { type: "document", format: "pptx", filename: "slides.pptx", size: 2048, duration: null, pages: 3, characters: 11 },
      transcription: null,
      text: "Slide text.",
    })

    expect(lecture.input_type).toBe("document")
    expect(lecture.transcript).toBeUndefined()
    expect(lecture.source_text).toBe("Slide text.")
    expect(lecture.source.characters).toBe(11)
  })

  it("puts every part of the notes in the detailed tab, except concepts and takeaways", () => {
    const detailed = text(toLecture(response()).notes.detailed)

    for (const part of [
      "An introduction.",
      "Explain overfitting",
      "When a model memorises its training data.",
      "Use a validation set",
      "Validation set: Data held back for checking a model",
      "A model that scores 100% in training",
      "Models must generalize.",
    ]) {
      expect(detailed).toContain(part)
    }
  })

  it("uses key points for short notes, and takeaways and concepts for important points", () => {
    const lecture = toLecture(response())

    expect(lecture.notes.short).toEqual([
      { type: "heading", level: 1, text: "Overfitting" },
      { type: "bullets", items: ["Use a validation set"] },
    ])
    expect(text(lecture.notes.important)).toContain("Test on unseen data")
    expect(text(lecture.notes.important)).toContain("Generalization")
  })

  it("leaves out headings that would have nothing under them", () => {
    const section = { ...notes.sections[0], definitions: [], examples: [] }
    const detailed = text(toLecture(response({ learning_objectives: [], sections: [section] })).notes.detailed)

    for (const heading of ["Learning objectives", "Definitions", "Examples"]) {
      expect(detailed).not.toContain(heading)
    }
  })

  it("marks short and important notes as missing when Gemini returned none", () => {
    const section = { ...notes.sections[0], key_points: [] }
    const lecture = toLecture(response({ sections: [section], important_concepts: [], key_takeaways: [] }))

    expect(lecture.notes.short).toBeNull()
    expect(lecture.notes.important).toBeNull()
  })
})

it("textToBlocks splits text into paragraphs at blank lines", () => {
  expect(textToBlocks("First slide.\n\n  \nSecond slide\nsame paragraph.")).toEqual([
    { type: "paragraph", text: "First slide." },
    { type: "paragraph", text: "Second slide\nsame paragraph." },
  ])
})

describe("transcript formatting", () => {
  it("shows timestamps as minutes and seconds", () => {
    expect(formatTimestamp(0)).toBe("0:00")
    expect(formatTimestamp(65.9)).toBe("1:05")
    expect(formatTimestamp(880)).toBe("14:40")
  })

  it("puts a timestamp on each copied line", () => {
    const copied = transcriptToText([
      { start: 0, end: 2, text: "Welcome." },
      { start: 62, end: 64, text: "Next topic." },
    ])

    expect(copied).toBe("[0:00] Welcome.\n[1:02] Next topic.")
  })
})
