import { useState, type ReactNode } from "react"
import { useNavigate } from "react-router"
import Button from "@/components/ui/Button"
import Icon, { type IconName } from "@/components/ui/Icon"
import Logo from "@/components/ui/Logo"

// Pages that exist in the design but aren't built yet are shown as "Soon".
const NAV_ITEMS: { label: string; icon: IconName }[] = [
  { label: "My lectures", icon: "folder" },
  { label: "Practice tests", icon: "question" },
  { label: "Scores", icon: "chart" },
]

export default function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="side-top">
          <Logo />
          <button className="mobile-close" onClick={() => setMenuOpen(false)} aria-label="Close navigation">
            <Icon name="close" />
          </button>
        </div>
        <Button icon="plus" className="new-project-button" onClick={() => navigate("/new")}>
          New lecture
        </Button>
        <nav className="side-nav" aria-label="Main navigation">
          <span className="nav-label">Workspace</span>
          {NAV_ITEMS.map((item) => (
            <button key={item.label} className="nav-item" disabled>
              <Icon name={item.icon} />
              <span>{item.label}</span>
              <small>Soon</small>
            </button>
          ))}
        </nav>
      </aside>
      {menuOpen && <button className="sidebar-scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
      <div className="app-main">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Open navigation">
            <Icon name="menu" />
          </button>
          <div className="topbar-spacer" />
        </header>
        {children}
      </div>
    </div>
  )
}
