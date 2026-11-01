import type { ReactNode } from "react"
import Icon, { type IconName } from "./Icon"

interface ButtonProps {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost" | "danger"
  icon?: IconName
  onClick?: () => void
  disabled?: boolean
  type?: "button" | "submit"
  className?: string
}

export default function Button({
  children,
  variant = "primary",
  icon,
  onClick,
  disabled,
  type = "button",
  className = "",
}: ButtonProps) {
  return (
    <button type={type} className={`btn btn-${variant} ${className}`} onClick={onClick} disabled={disabled}>
      {icon && <Icon name={icon} size={18} />}
      <span>{children}</span>
    </button>
  )
}
