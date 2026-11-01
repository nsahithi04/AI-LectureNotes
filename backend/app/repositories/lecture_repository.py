"""Where lectures are kept.

For now this is an in-memory dictionary, so everything is lost when the server restarts.
No database has been chosen yet. Adding one only requires changing this file: the rest of the app
only calls `save`, `get` and `list_all`.
"""

from typing import Optional

from app.schemas.lecture import LectureRecord


class InMemoryLectureRepository:
    def __init__(self) -> None:
        self._lectures: dict[str, LectureRecord] = {}

    def save(self, lecture: LectureRecord) -> LectureRecord:
        self._lectures[lecture.id] = lecture
        return lecture

    def get(self, lecture_id: str) -> Optional[LectureRecord]:
        return self._lectures.get(lecture_id)

    def list_all(self) -> list[LectureRecord]:
        return sorted(self._lectures.values(), key=lambda lecture: lecture.created_at, reverse=True)


lecture_repository = InMemoryLectureRepository()
