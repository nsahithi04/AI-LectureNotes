import { useNavigate } from "react-router"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"
import Icon, { type IconName } from "@/components/ui/Icon"
import Logo from "@/components/ui/Logo"

const STEPS: [string, string, string, IconName][] = [
  ["01", "Add your lecture", "Upload a video, audio recording, slides or handouts, or paste the lecture text.", "upload"],
  ["02", "Choose your notes", "Pick a detailed transcript, short revision notes, important points, or all three.", "note"],
  ["03", "Study and test yourself", "Read your notes, then turn them into a practice test to check what you've learned.", "question"],
]

const FEATURES: [IconName, string, string, boolean?][] = [
  ["text", "Detailed transcript", "The full lecture, organized into topics, subtopics and body text."],
  ["note", "Short notes", "Only the main points of each topic, ideal for revision."],
  ["spark", "Important points", "The key takeaways in a list you can skim in a minute."],
  ["question", "Practice tests", "Multiple-choice or written questions generated from your notes.", true],
  ["chart", "Automatic scoring", "Your answers are evaluated and scored.", true],
]

export default function LandingPage() {
  const navigate = useNavigate()
  const start = () => navigate("/new")

  return (
    <div className="landing">
      <header className="marketing-header">
        <Logo />
        <nav>
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
        </nav>
        <div className="header-actions">
          <Button onClick={start}>Get started</Button>
        </div>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="announcement">
              <Icon name="spark" size={15} />
              Long lectures, made learnable
            </div>
            <h1>
              Turn lectures into
              <br />
              <em>structured notes.</em>
            </h1>
            <p>
              Upload a lecture video, audio recording, slides, handouts or text. Get a detailed transcript, short revision notes and
              the important points, then test yourself.
            </p>
            <div className="hero-actions">
              <Button onClick={start} icon="arrow">
                Start with a lecture
              </Button>
              <Button variant="secondary" icon="eye" onClick={() => navigate("/preview")}>
                See sample notes
              </Button>
            </div>
          </div>
          <div className="product-preview">
            <div className="preview-bar">
              <div className="preview-dots">
                <i />
                <i />
                <i />
              </div>
              <span>Introduction to Machine Learning</span>
              <Badge label="Ready" tone="success" />
            </div>
            <div className="preview-body">
              <div className="preview-nav">
                <Logo />
                <div className="preview-nav-lines">
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
              </div>
              <div className="preview-content">
                <span className="mini-label">SHORT NOTES</span>
                <h3>Core Concepts in Machine Learning</h3>
                <p>Machine learning enables systems to learn patterns from data and improve without explicit programming.</p>
                <div className="concept-card">
                  <div className="concept-icon">
                    <Icon name="spark" />
                  </div>
                  <div>
                    <strong>Supervised learning</strong>
                    <span>Learns from labeled examples to make predictions on new data.</span>
                  </div>
                </div>
                <div className="concept-card">
                  <div className="concept-icon blue">
                    <Icon name="chart" />
                  </div>
                  <div>
                    <strong>Model evaluation</strong>
                    <span>Measures how well a model generalizes beyond its training data.</span>
                  </div>
                </div>
                <div className="note-lines">
                  <i />
                  <i />
                  <i />
                </div>
              </div>
              <div className="preview-panel">
                <span className="mini-label">GENERATED</span>
                <div>
                  <Icon name="check" size={15} />
                  Detailed transcript
                </div>
                <div>
                  <Icon name="check" size={15} />
                  Short notes
                </div>
                <div>
                  <Icon name="check" size={15} />
                  Important points
                </div>
              </div>
            </div>
          </div>
        </section>
        <section className="input-strip">
          <p>One workspace for every kind of lecture</p>
          <div>
            <span>
              <Icon name="video" />
              Video lectures <small>MP4, MOV</small>
            </span>
            <span>
              <Icon name="audio" />
              Audio recordings <small>MP3, WAV, M4A</small>
            </span>
            <span>
              <Icon name="pdf" />
              Slides & handouts <small>PDF, Word, PowerPoint</small>
            </span>
            <span>
              <Icon name="text" />
              Text & transcripts <small>Paste any text</small>
            </span>
          </div>
        </section>
        <section className="how-section" id="how">
          <div className="section-heading">
            <span>HOW IT WORKS</span>
            <h2>From lecture to learning in three steps</h2>
            <p>Spend less time reading and rewatching, and more time understanding.</p>
          </div>
          <div className="steps-grid">
            {STEPS.map(([number, title, text, icon]) => (
              <article className="step-card" key={number}>
                <div className="step-top">
                  <span>{number}</span>
                  <div>
                    <Icon name={icon} />
                  </div>
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="features-section" id="features">
          <div className="feature-intro">
            <span className="eyebrow">BUILT FOR STUDENTS</span>
            <h2>Three kinds of notes for every way you study.</h2>
            <p>Read it in full, revise the main points, or skim the essentials before an exam.</p>
            <Button variant="secondary" onClick={start}>
              Try it with a lecture
            </Button>
          </div>
          <div className="feature-list">
            {FEATURES.map(([icon, title, text, soon]) => (
              <div className="feature-row" key={title}>
                <div className="feature-icon">
                  <Icon name={icon} />
                </div>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
                {soon && <Badge label="Coming soon" tone="primary" />}
              </div>
            ))}
          </div>
        </section>
      </main>
      <footer>
        <Logo />
        <p>Make every lecture easier to learn from.</p>
        <span>© 2026 LectureAI</span>
      </footer>
    </div>
  )
}
