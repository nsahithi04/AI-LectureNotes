import { Link } from "react-router"
import Icon from "./Icon"

export default function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="logo">
      <span className="logo-mark">
        <Icon name="spark" size={20} />
      </span>
      <span>
        Lecture<span>AI</span>
      </span>
    </Link>
  )
}
