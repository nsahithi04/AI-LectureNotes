import Icon from "./Icon"

type Tone = "success" | "info" | "danger" | "primary"

// Maps a tone to the badge colour classes defined in index.css.
const TONE_CLASS: Record<Tone, string> = {
  success: "badge-completed",
  info: "badge-processing",
  danger: "badge-failed",
  primary: "badge-coming-soon",
}

export default function Badge({ label, tone }: { label: string; tone: Tone }) {
  const icon = tone === "success" ? "check" : tone === "danger" ? "error" : "clock"
  return (
    <span className={`badge ${TONE_CLASS[tone]}`}>
      <Icon name={icon} size={13} />
      {label}
    </span>
  )
}
