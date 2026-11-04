import { useEffect, useRef, useState } from "react"
import Button from "@/components/ui/Button"
import Icon from "@/components/ui/Icon"
import PageHeader from "@/components/ui/PageHeader"
import { generateQuestions } from "@/services/api"
import type { SavedForm } from "@/services/googleForms"
import { loadSavedForms, saveForm } from "@/services/savedForms"
import type { Question } from "@/types/lecture"
import { questionsToText, type QuizQuestion } from "@/utils/quiz"
import FormDetails from "./FormDetails"
import GoogleFormPanel from "./GoogleFormPanel"
import QuestionCard from "./QuestionCard"
import QuestionEditor from "./QuestionEditor"
import QuizSetupForm, { type QuizSetup } from "./QuizSetupForm"
import SavedFormsList from "./SavedFormsList"

const INITIAL_SETUP: QuizSetup = { count: 10, questionType: "multiple_choice", instructions: "" }

/** The teacher's quiz flow: choose the settings, generate questions, then pick, edit and add to them. */
export default function QuizBuilder({ title, text }: { title: string; text: string }) {
  const [setup, setSetup] = useState(INITIAL_SETUP)
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<number | "new" | null>(null)
  const [copied, setCopied] = useState(false)
  const [savedForms, setSavedForms] = useState<SavedForm[]>(loadSavedForms)
  const [createdFormId, setCreatedFormId] = useState<string | null>(null)
  const nextId = useRef(1)

  // There's no database yet, so a refresh would lose the teacher's selection.
  const hasWork = generating || questions !== null
  useEffect(() => {
    if (!hasWork) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [hasWork])

  function withId(question: Question): QuizQuestion {
    return { ...question, id: nextId.current++, selected: true }
  }

  async function handleGenerate() {
    setGenerating(true)
    setError(null)
    try {
      const generated = await generateQuestions({
        transcript: text,
        count: setup.count,
        question_type: setup.questionType,
        instructions: setup.instructions.trim() || null,
      })
      setQuestions(generated.map(withId))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setGenerating(false)
    }
  }

  function saveQuestion(question: Question) {
    setQuestions((current) => {
      if (editing === "new") return [...(current ?? []), withId(question)]
      return (current ?? []).map((item) => (item.id === editing ? { ...item, ...question } : item))
    })
    setEditing(null)
  }

  function handleFormChange(form: SavedForm) {
    setSavedForms(saveForm(form))
  }

  function handleFormCreated(form: SavedForm) {
    setSavedForms(saveForm(form))
    setCreatedFormId(form.formId)
  }

  function updateAll(selected: boolean) {
    setQuestions((current) => (current ?? []).map((item) => ({ ...item, selected })))
  }

  if (generating) {
    return (
      <div className="quiz-builder" role="status">
        <PageHeader eyebrow="QUIZ" title="Writing your questions" subtitle="This can take a few minutes. Keep this page open." />
        <div className="quiz-loading">
          <i className="spinner" />
          Generating {setup.count} question{setup.count === 1 ? "" : "s"} from the lecture
        </div>
      </div>
    )
  }

  if (!questions) {
    return (
      <div className="quiz-builder">
        <PageHeader eyebrow="QUIZ" title="Create a quiz" subtitle="Tell us what you need, then choose the questions you like." />
        {error && (
          <div className="failure-box submit-error" role="alert">
            <Icon name="error" />
            <div>
              <strong>We couldn’t generate questions</strong>
              <span>{error}</span>
            </div>
          </div>
        )}
        <QuizSetupForm setup={setup} onChange={setSetup} onGenerate={handleGenerate} />
        <SavedFormsList forms={savedForms} onChange={handleFormChange} />
      </div>
    )
  }

  const selected = questions.filter((question) => question.selected)
  const createdForm = savedForms.find((form) => form.formId === createdFormId)

  async function copyQuestions() {
    await navigator.clipboard.writeText(questionsToText(selected))
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="quiz-builder">
      <PageHeader eyebrow="QUIZ" title="Choose your questions" subtitle="Untick any you don’t want, edit them, or add your own." />
      <div className="quiz-summary">
        <div>
          <strong>
            {selected.length} of {questions.length} selected
          </strong>
        </div>
        <div className="quiz-question-actions">
          <Button variant="ghost" onClick={() => updateAll(true)}>
            Select all
          </Button>
          <Button variant="ghost" onClick={() => updateAll(false)}>
            Clear
          </Button>
          <Button variant="ghost" icon="copy" disabled={!selected.length} onClick={copyQuestions}>
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </div>
      <div className="quiz-list">
        {questions.map((question, index) =>
          editing === question.id ? (
            <QuestionEditor key={question.id} question={question} onSave={saveQuestion} onCancel={() => setEditing(null)} />
          ) : (
            <QuestionCard
              key={question.id}
              question={question}
              number={index + 1}
              onToggle={() =>
                setQuestions(questions.map((item) => (item.id === question.id ? { ...item, selected: !item.selected } : item)))
              }
              onEdit={() => setEditing(question.id)}
              onDelete={() => setQuestions(questions.filter((item) => item.id !== question.id))}
            />
          ),
        )}
      </div>
      <div className="quiz-add">
        {editing === "new" ? (
          <QuestionEditor onSave={saveQuestion} onCancel={() => setEditing(null)} />
        ) : (
          <div className="quiz-actions">
            <Button
              variant="secondary"
              onClick={() => {
                setQuestions(null)
                setCreatedFormId(null)
              }}
            >
              Start over
            </Button>
            <Button variant="secondary" icon="plus" onClick={() => setEditing("new")}>
              Add your own question
            </Button>
          </div>
        )}
      </div>
      {editing === null && (
        <div className="quiz-share">
          {createdForm ? (
            <FormDetails form={createdForm} onChange={handleFormChange} />
          ) : (
            <GoogleFormPanel title={title} questions={selected} onCreated={handleFormCreated} />
          )}
        </div>
      )}
    </div>
  )
}
