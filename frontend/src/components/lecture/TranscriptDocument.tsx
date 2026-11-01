import type { TranscriptSegment } from "@/types/lecture"
import { formatTimestamp } from "@/utils/format"

interface TranscriptDocumentProps {
  title: string
  segments: TranscriptSegment[]
}

export default function TranscriptDocument({ title, segments }: TranscriptDocumentProps) {
  return (
    <article className="document">
      <div className="doc-kicker">TRANSCRIPT</div>
      <h1>{title}</h1>
      <hr />
      {segments.map((segment) => (
        <div className="transcript-row" key={segment.start}>
          <time>{formatTimestamp(segment.start)}</time>
          <p>{segment.text}</p>
        </div>
      ))}
    </article>
  )
}
