import { useNavigate } from "react-router"
import Button from "@/components/ui/Button"
import Logo from "@/components/ui/Logo"

interface StepHeaderProps {
  step: 1 | 2
  title: string
}

export default function StepHeader({ step, title }: StepHeaderProps) {
  const navigate = useNavigate()
  return (
    <div className="flow-top">
      <div className="flow-logo">
        <Logo />
      </div>
      <div className="flow-progress">
        <span>STEP {step} OF 2</span>
        <div>
          <i className="done" />
          <i className={step === 2 ? "done" : ""} />
        </div>
        <strong>{title}</strong>
      </div>
      <Button variant="ghost" onClick={() => navigate("/")}>
        Cancel
      </Button>
    </div>
  )
}
