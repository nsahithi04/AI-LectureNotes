import { useNavigate } from "react-router"
import Button from "@/components/ui/Button"
import EmptyState from "@/components/ui/EmptyState"

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <main className="page not-found-page">
      <EmptyState
        icon="search"
        title="Page not found"
        text="The page you're looking for doesn't exist."
        action={<Button onClick={() => navigate("/")}>Go home</Button>}
      />
    </main>
  )
}
