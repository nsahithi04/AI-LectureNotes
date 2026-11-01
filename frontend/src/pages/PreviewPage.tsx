import AppShell from "@/components/layout/AppShell"
import ResultsView from "@/components/lecture/ResultsView"
import { sampleLecture } from "@/data/sampleLecture"

/** The results screen filled with sample notes: shows the shape the backend's notes should take. */
export default function PreviewPage() {
  return (
    <AppShell>
      <div className="sample-banner">Sample preview: these notes are example data, not generated from an upload.</div>
      <ResultsView lecture={sampleLecture} />
    </AppShell>
  )
}
