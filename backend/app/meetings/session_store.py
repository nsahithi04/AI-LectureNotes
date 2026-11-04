"""Where meeting sessions and their transcripts are kept.

DEVELOPMENT ONLY. Sessions are JSON files on this server's disk, with no user accounts, encryption or
access control. Real use needs a database with per-user access. The rest of the meetings code only calls
the SessionStore methods, so swapping the storage won't change anything else.
"""

import os
import re
import threading
from pathlib import Path
from typing import Optional, Protocol

from app.meetings.errors import MeetingError
from app.meetings.schemas import MeetingSession, TranscriptSegment

SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


class SessionStore(Protocol):
    def save(self, session: MeetingSession) -> MeetingSession: ...
    def get(self, session_id: str) -> Optional[MeetingSession]: ...
    def all(self) -> list[MeetingSession]: ...
    def add_segments(self, session_id: str, segments: list[TranscriptSegment]) -> None: ...
    def get_segments(self, session_id: str) -> list[TranscriptSegment]: ...


def _sorted(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    return sorted(segments, key=lambda segment: (segment.start_time, segment.id))


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, MeetingSession] = {}
        self._segments: dict[str, list[TranscriptSegment]] = {}

    def save(self, session: MeetingSession) -> MeetingSession:
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[MeetingSession]:
        return self._sessions.get(session_id)

    def all(self) -> list[MeetingSession]:
        return sorted(self._sessions.values(), key=lambda s: s.started_at.timestamp() if s.started_at else 0, reverse=True)

    def add_segments(self, session_id: str, segments: list[TranscriptSegment]) -> None:
        self._segments.setdefault(session_id, []).extend(segments)

    def get_segments(self, session_id: str) -> list[TranscriptSegment]:
        return _sorted(self._segments.get(session_id, []))


class JsonFileSessionStore:
    """One folder per session: session.json, and transcript.jsonl with one segment per line."""

    def __init__(self, root: Path):
        self.root = root
        self._lock = threading.Lock()

    def _folder(self, session_id: str) -> Path:
        if not SESSION_ID.match(session_id):
            raise MeetingError("session_not_found", "Meeting session not found.")
        return self.root / session_id

    def save(self, session: MeetingSession) -> MeetingSession:
        folder = self._folder(session.id)
        with self._lock:
            folder.mkdir(parents=True, exist_ok=True)
            temp = folder / "session.json.tmp"
            temp.write_text(session.model_dump_json(indent=2))
            os.replace(temp, folder / "session.json")  # never leaves a half-written file
        return session

    def get(self, session_id: str) -> Optional[MeetingSession]:
        path = self._folder(session_id) / "session.json"
        return MeetingSession.model_validate_json(path.read_text()) if path.is_file() else None

    def all(self) -> list[MeetingSession]:
        if not self.root.is_dir():
            return []
        sessions = [MeetingSession.model_validate_json(p.read_text()) for p in self.root.glob("*/session.json")]
        return sorted(sessions, key=lambda s: s.started_at.timestamp() if s.started_at else 0, reverse=True)

    def add_segments(self, session_id: str, segments: list[TranscriptSegment]) -> None:
        folder = self._folder(session_id)
        with self._lock:
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "transcript.jsonl").open("a") as out:
                for segment in segments:
                    out.write(segment.model_dump_json() + "\n")

    def get_segments(self, session_id: str) -> list[TranscriptSegment]:
        path = self._folder(session_id) / "transcript.jsonl"
        if not path.is_file():
            return []
        return _sorted([TranscriptSegment.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()])
