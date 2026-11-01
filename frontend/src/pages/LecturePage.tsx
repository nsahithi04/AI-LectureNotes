import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router"
import AppShell from "@/components/layout/AppShell"
import ProcessingView from "@/components/lecture/ProcessingView"
import ResultsView from "@/components/lecture/ResultsView"
import Button from "@/components/ui/Button"
import EmptyState from "@/components/ui/EmptyState"
import { getLecture } from "@/services/api"
import type { Lecture } from "@/types/lecture"

const POLL_INTERVAL_MS = 3000

/** Shows a lecture's progress while it's being processed, then its notes once it's completed. */
export default function LecturePage() {
  const { lectureId = "" } = useParams()
  const navigate = useNavigate()
  const [lecture, setLecture] = useState<Lecture | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>

    async function load() {
      try {
        const data = await getLecture(lectureId)
        if (cancelled) return
        setLecture(data)
        setError(null)
        // Keep checking until processing has finished one way or the other.
        if (data.status === "uploaded" || data.status === "processing") {
          timer = setTimeout(load, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load this lecture.")
      }
    }

    load()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [lectureId])

  let content
  if (error) {
    content = (
      <main className="page">
        <EmptyState
          icon="error"
          title="Couldn't load this lecture"
          text={error}
          action={<Button icon="plus" onClick={() => navigate("/new")}>New lecture</Button>}
        />
      </main>
    )
  } else if (!lecture) {
    content = <main className="page loading-page">Loading lecture...</main>
  } else if (lecture.status === "completed") {
    content = <ResultsView lecture={lecture} />
  } else {
    content = <ProcessingView lecture={lecture} />
  }

  return <AppShell>{content}</AppShell>
}
