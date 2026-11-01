import { useLocation, useNavigate } from "react-router"
import AppShell from "@/components/layout/AppShell"
import ResultsView from "@/components/lecture/ResultsView"
import Button from "@/components/ui/Button"
import EmptyState from "@/components/ui/EmptyState"
import type { Lecture } from "@/types/lecture"

/** Shows the notes just generated. There's no database yet, so they travel in the browser's history entry. */
export default function GeneratedNotesPage() {
  const navigate = useNavigate()
  const lecture = (useLocation().state as { lecture?: Lecture } | null)?.lecture

  return (
    <AppShell>
      {lecture ? (
        <ResultsView lecture={lecture} />
      ) : (
        <main className="page">
          <EmptyState
            icon="note"
            title="No notes to show"
            text="Notes aren't saved yet, so upload a lecture to generate them."
            action={<Button icon="plus" onClick={() => navigate("/new")}>New lecture</Button>}
          />
        </main>
      )}
    </AppShell>
  )
}
