import type { ReactNode } from "react"
import Icon, { type IconName } from "./Icon"

interface EmptyStateProps {
  icon: IconName
  title: string
  text: string
  action?: ReactNode
}

export default function EmptyState({ icon, title, text, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div>
        <Icon name={icon} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  )
}
