import { useState } from "react"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"
import EmptyState from "@/components/ui/EmptyState"
import Icon from "@/components/ui/Icon"
import { NOTE_OPTIONS, TRANSCRIPT_OPTION, getInputOption, getNoteOption } from "@/data/options"
import type { Lecture, NoteType } from "@/types/lecture"
import { blocksToText, countWords, formatDate, formatFileSize, transcriptToText } from "@/utils/format"
import NoteDocument from "./NoteDocument"
import TranscriptDocument from "./TranscriptDocument"

export default function ResultsView({ lecture }: { lecture: Lecture }) {
  const [tab, setTab] = useState<NoteType | "transcript">(lecture.note_types[0] ?? "detailed")
  const [copied, setCopied] = useState(false)

  const showTranscript = tab === "transcript"
  const option = showTranscript ? TRANSCRIPT_OPTION : getNoteOption(tab)
  const blocks = showTranscript ? null : lecture.notes[tab]
  const plainText = showTranscript ? transcriptToText(lecture.transcript ?? []) : blocks ? blocksToText(blocks) : ""
  const words = countWords(plainText)

  async function copyNotes() {
    await navigator.clipboard.writeText(plainText)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <main className="results-page">
      <div className="results-head">
        <div className="results-title">
          <div>
            <h1>{lecture.title}</h1>
            <span>
              <Badge label="Completed" tone="success" /> Created {formatDate(lecture.created_at)}
            </span>
          </div>
        </div>
      </div>
      <div className="document-workspace">
        <aside className="output-nav">
          <span>YOUR NOTES</span>
          {NOTE_OPTIONS.map((note) => (
            <button className={tab === note.type ? "active" : ""} onClick={() => setTab(note.type)} key={note.type}>
              <div>
                <Icon name={note.icon} size={18} />
                <span>{note.title}</span>
              </div>
              <Icon name="chevron" size={15} />
            </button>
          ))}
          {lecture.transcript && (
            <button className={showTranscript ? "active" : ""} onClick={() => setTab("transcript")}>
              <div>
                <Icon name={TRANSCRIPT_OPTION.icon} size={18} />
                <span>{TRANSCRIPT_OPTION.title}</span>
              </div>
              <Icon name="chevron" size={15} />
            </button>
          )}
          <button disabled className="nav-soon">
            <div>
              <Icon name="question" size={18} />
              <span>Practice test</span>
            </div>
            <small>Soon</small>
          </button>
          <div className="source-link">
            <span>SOURCE</span>
            <div className="source-item">
              <Icon name={lecture.input_type} />
              <span>
                <strong>{getInputOption(lecture.input_type).title}</strong>
                <small>
                  {lecture.source.filename
                    ? formatFileSize(lecture.source.file_size ?? 0)
                    : `${(lecture.source.characters ?? 0).toLocaleString()} characters`}
                </small>
              </span>
            </div>
          </div>
        </aside>
        <section className="document-view">
          {plainText ? (
            <>
              <div className="doc-toolbar">
                <div>
                  <Button variant="ghost" icon="copy" onClick={copyNotes}>
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>
              {blocks ? (
                <NoteDocument kicker={option.title.toUpperCase()} title={lecture.title} blocks={blocks} />
              ) : (
                <TranscriptDocument title={lecture.title} segments={lecture.transcript ?? []} />
              )}
            </>
          ) : (
            <EmptyState
              icon={option.icon}
              title={`No ${option.title.toLowerCase()} yet`}
              text={
                showTranscript || lecture.note_types.includes(tab)
                  ? "These notes haven't been generated."
                  : "This note type wasn't selected when the lecture was uploaded."
              }
            />
          )}
        </section>
        <aside className="document-info">
          <span>DOCUMENT INFO</span>
          <dl>
            <div>
              <dt>Created</dt>
              <dd>{formatDate(lecture.created_at)}</dd>
            </div>
            <div>
              <dt>Words</dt>
              <dd>{words.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Reading time</dt>
              <dd>{Math.max(1, Math.round(words / 200))} min</dd>
            </div>
          </dl>
          <hr />
          <div className="info-tip">
            <Icon name="spark" />
            <p>
              <strong>{option.title}</strong>
              {option.description}
            </p>
          </div>
        </aside>
      </div>
    </main>
  )
}
