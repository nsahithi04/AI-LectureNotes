// Remembers the Google Forms this browser created, so the teacher can come back for results.
// There's no database yet, so they're only on this browser and are lost if its site data is cleared.
import type { SavedForm } from "./googleForms"

const STORAGE_KEY = "lectureai.googleForms"

export function loadSavedForms(): SavedForm[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]")
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

export function saveForm(form: SavedForm): SavedForm[] {
  const forms = [form, ...loadSavedForms().filter((saved) => saved.formId !== form.formId)]
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(forms))
  } catch {
    // Storage can be full or blocked. The form still exists in Google Forms, so carry on.
  }
  return forms
}
