import type { GeneratedNotes, Lecture, NoteBlock, VideoProcessData } from "@/types/lecture"

function bulletSection(heading: string, level: 1 | 2, items: string[]): NoteBlock[] {
  return items.length ? [{ type: "heading", level, text: heading }, { type: "bullets", items }] : []
}

function detailedBlocks(notes: GeneratedNotes): NoteBlock[] {
  return [
    { type: "heading", level: 1, text: "Overview" },
    { type: "paragraph", text: notes.overview },
    ...bulletSection("Learning objectives", 1, notes.learning_objectives),
    ...notes.sections.flatMap((section): NoteBlock[] => [
      { type: "heading", level: 1, text: section.heading },
      { type: "paragraph", text: section.content },
      ...bulletSection("Key points", 2, section.key_points),
      ...bulletSection(
        "Definitions",
        2,
        section.definitions.map(({ term, meaning }) => `${term}: ${meaning}`),
      ),
      ...bulletSection("Examples", 2, section.examples),
    ]),
    { type: "heading", level: 1, text: "Conclusion" },
    { type: "paragraph", text: notes.conclusion },
  ]
}

function shortBlocks(notes: GeneratedNotes): NoteBlock[] {
  return notes.sections.flatMap((section) => bulletSection(section.heading, 1, section.key_points))
}

function importantBlocks(notes: GeneratedNotes): NoteBlock[] {
  return [
    ...bulletSection("Key takeaways", 1, notes.key_takeaways),
    ...bulletSection("Important concepts", 1, notes.important_concepts),
  ]
}

/** Turn the backend's response into the Lecture shape the results screen displays. */
export function toLecture({ video, transcription, lecture_notes: notes }: VideoProcessData): Lecture {
  const short = shortBlocks(notes)
  const important = importantBlocks(notes)
  return {
    id: "generated",
    title: notes.title,
    input_type: "video",
    status: "completed",
    note_types: ["detailed", "short", "important"],
    source: { filename: video.filename, file_size: video.size, characters: null },
    notes: {
      detailed: detailedBlocks(notes),
      short: short.length ? short : null,
      important: important.length ? important : null,
    },
    transcript: transcription.segments,
    error: null,
    created_at: new Date().toISOString(),
  }
}
