import type { NoteBlock } from "@/types/lecture"

interface NoteDocumentProps {
  kicker: string
  title: string
  blocks: NoteBlock[]
}

/** Renders note blocks: level-1 headings are topics, level-2 headings are subtopics. */
export default function NoteDocument({ kicker, title, blocks }: NoteDocumentProps) {
  return (
    <article className="document">
      <div className="doc-kicker">{kicker}</div>
      <h1>{title}</h1>
      <hr />
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          return block.level === 1 ? <h2 key={index}>{block.text}</h2> : <h3 key={index}>{block.text}</h3>
        }
        if (block.type === "bullets") {
          return (
            <ul key={index}>
              {block.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )
        }
        return <p key={index}>{block.text}</p>
      })}
    </article>
  )
}
