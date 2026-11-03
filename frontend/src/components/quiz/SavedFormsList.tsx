import FormDetails from "./FormDetails"
import type { SavedForm } from "@/services/googleForms"

interface SavedFormsListProps {
  forms: SavedForm[]
  onChange: (form: SavedForm) => void
}

/** Google Forms created on this browser, so the teacher can come back for results. */
export default function SavedFormsList({ forms, onChange }: SavedFormsListProps) {
  if (!forms.length) return null
  return (
    <section className="quiz-saved">
      <h2>Your Google Forms</h2>
      <p className="quiz-note">Saved on this browser only, until LectureAI has accounts.</p>
      <div className="quiz-list">
        {forms.map((form) => (
          <FormDetails key={form.formId} form={form} onChange={onChange} />
        ))}
      </div>
    </section>
  )
}
