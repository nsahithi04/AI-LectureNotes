import os
import stat
from datetime import datetime, timezone

import pytest

from app.meetings.errors import MeetingError
from app.meetings.schemas import MeetingSession, ProcessingMode, ProviderId, TranscriptSegment
from app.meetings.session_store import InMemorySessionStore, JsonFileSessionStore
from app.meetings.token_store import DevFileTokenStore


def session(session_id="s1", hour=10):
    return MeetingSession(
        id=session_id,
        provider=ProviderId.ZOOM,
        provider_meeting_id="123",
        title="ML lecture",
        started_at=datetime(2026, 11, 3, hour, tzinfo=timezone.utc),
        processing_mode=ProcessingMode.LIVE,
    )


def segment(segment_id, start):
    return TranscriptSegment(id=segment_id, start_time=start, end_time=start + 1, text=f"At {start}.", source="zoom_rtms")


@pytest.fixture(params=["memory", "files"])
def store(request, tmp_path):
    return InMemorySessionStore() if request.param == "memory" else JsonFileSessionStore(tmp_path / "sessions")


def test_sessions_are_saved_listed_newest_first_and_updated(store):
    store.save(session("old", hour=9))
    store.save(session("new", hour=11))
    updated = session("old", hour=9).model_copy(update={"title": "Renamed"})
    store.save(updated)

    assert [s.id for s in store.all()] == ["new", "old"]
    assert store.get("old").title == "Renamed"
    assert store.get("missing") is None


def test_transcript_segments_are_appended_and_returned_in_time_order(store):
    store.save(session())
    store.add_segments("s1", [segment("a", 5), segment("b", 1)])
    store.add_segments("s1", [segment("c", 3)])

    assert [s.id for s in store.get_segments("s1")] == ["b", "c", "a"]
    assert store.get_segments("other") == []


def test_file_store_rejects_ids_that_could_escape_its_folder(tmp_path):
    store = JsonFileSessionStore(tmp_path / "sessions")

    with pytest.raises(MeetingError):
        store.get("../../secrets")


def test_file_store_survives_a_restart(tmp_path):
    JsonFileSessionStore(tmp_path / "sessions").save(session())

    assert JsonFileSessionStore(tmp_path / "sessions").get("s1").title == "ML lecture"


def test_tokens_are_saved_per_user_and_provider_and_readable_only_by_the_owner(tmp_path):
    tokens = DevFileTokenStore(tmp_path / "tokens.json")
    tokens.save("zoom", "teacher-1", {"access_token": "abc", "refresh_token": "def"})
    tokens.save("google_meet", "teacher-1", {"access_token": "ghi"})

    assert tokens.get("zoom", "teacher-1")["refresh_token"] == "def"
    assert tokens.get("zoom", "teacher-2") is None
    assert tokens.connected_providers("teacher-1") == ["google_meet", "zoom"]
    assert stat.S_IMODE(os.stat(tmp_path / "tokens.json").st_mode) == 0o600

    tokens.delete("zoom", "teacher-1")
    assert tokens.connected_providers("teacher-1") == ["google_meet"]
