import type { NoteBlock, TranscriptSegment } from "@/types/lecture"

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ["KB", "MB", "GB"]
  let size = bytes / 1024
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(size < 10 ? 1 : 0)} ${units[unit]}`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
}

/** Plain-text version of note blocks, used for copying and word counts. */
export function blocksToText(blocks: NoteBlock[]): string {
  return blocks
    .map((block) => {
      if (block.type === "bullets") return block.items.map((item) => `• ${item}`).join("\n")
      return block.text
    })
    .join("\n\n")
}

export function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`
}

/** Plain-text version of a transcript, used for copying and word counts. */
export function transcriptToText(segments: TranscriptSegment[]): string {
  return segments.map((segment) => `[${formatTimestamp(segment.start)}] ${segment.text}`).join("\n")
}

/** Pasted or document text as paragraphs, split at blank lines. */
export function textToBlocks(text: string): NoteBlock[] {
  return text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => ({ type: "paragraph", text: paragraph }))
}

export function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length
}
