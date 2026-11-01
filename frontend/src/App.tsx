import { Route, Routes } from "react-router"
import GeneratedNotesPage from "@/pages/GeneratedNotesPage"
import LandingPage from "@/pages/LandingPage"
import LecturePage from "@/pages/LecturePage"
import NewLecturePage from "@/pages/NewLecturePage"
import NotFoundPage from "@/pages/NotFoundPage"
import PreviewPage from "@/pages/PreviewPage"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/new" element={<NewLecturePage />} />
      <Route path="/notes" element={<GeneratedNotesPage />} />
      <Route path="/lectures/:lectureId" element={<LecturePage />} />
      <Route path="/preview" element={<PreviewPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
