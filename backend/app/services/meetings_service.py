"""Connects the meeting endpoints to the meetings layer and the AI engine.

It builds the providers from the settings, imports a finished meeting's transcript into a session, and
turns that transcript into lecture notes. Tests replace the registry and stores with temporary versions.
"""

import secrets
from typing import Optional

from starlette.concurrency import run_in_threadpool

from app.core import config
from app.engine import pipeline
from app.engine.schemas import LectureResult
from app.meetings.errors import MeetingError
from app.meetings.oauth import OAuthStateStore
from app.meetings.providers.google_meet import GoogleMeetProvider
from app.meetings.providers.registry import GOOGLE_MEET, ProviderRegistry, build_registry
from app.meetings.schemas import (
    MeetingSession,
    ProcessingMode,
    SessionStatus,
    TranscriptSegment,
    TranscriptStatus,
)
from app.meetings.session_store import JsonFileSessionStore, SessionStore
from app.meetings.token_store import DevFileTokenStore, TokenStore


def callback_url(provider_id: str) -> str:
    """Where a provider sends the teacher back after signing in. It must be registered with the provider."""
    return f"{config.BACKEND_PUBLIC_URL}/api/meetings/{provider_id}/callback"


def create_registry(tokens: TokenStore, states: OAuthStateStore, google_transport=None) -> ProviderRegistry:
    google_meet = GoogleMeetProvider(
        GOOGLE_MEET,
        client_id=config.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=config.GOOGLE_OAUTH_CLIENT_SECRET,
        redirect_uri=callback_url(GOOGLE_MEET.id.value),
        tokens=tokens,
        states=states,
        transport=google_transport,
    )
    return build_registry(google_meet=google_meet)


sessions: SessionStore = JsonFileSessionStore(config.MEETINGS_STORAGE_DIR / "sessions")
tokens: TokenStore = DevFileTokenStore(config.MEETINGS_STORAGE_DIR / "tokens.json")
states = OAuthStateStore()
registry = create_registry(tokens, states)


def get_session(session_id: str) -> MeetingSession:
    session = sessions.get(session_id)
    if session is None:
        raise MeetingError("session_not_found", "Meeting session not found.")
    return session


async def import_meeting(provider_id: str, provider_meeting_id: str, user_id: str) -> MeetingSession:
    """Copy a finished meeting's transcript into a LectureAI session. Importing it again returns the same session."""
    provider = registry.get(provider_id)
    for session in sessions.all():
        if (
            session.provider == provider.info.id
            and session.provider_meeting_id == provider_meeting_id
            and session.status == SessionStatus.COMPLETED
        ):
            return session

    details = await provider.get_meeting_details(user_id, provider_meeting_id)
    if details.transcript_status == TranscriptStatus.PROCESSING:
        raise MeetingError("transcript_not_ready", "This meeting's transcript isn't ready yet. Try again in a few minutes.")
    if details.transcript_status == TranscriptStatus.NONE:
        raise MeetingError(
            "no_transcript", "This meeting has no transcript. Transcription has to be turned on during the meeting."
        )

    session_id = f"{provider.info.id.value}-{secrets.token_hex(6)}"
    segments = await provider.retrieve_transcript(user_id, provider_meeting_id, session_id)
    if not segments:
        raise MeetingError("no_transcript", "This meeting's transcript is empty.")

    session = MeetingSession(
        id=session_id,
        provider=provider.info.id,
        provider_meeting_id=provider_meeting_id,
        title=details.title,
        status=SessionStatus.COMPLETED,
        started_at=details.started_at,
        ended_at=details.ended_at,
        participants=details.participants,
        processing_mode=ProcessingMode.POST_MEETING,
    )
    sessions.add_segments(session_id, segments)
    sessions.save(session)
    return session


def _timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def transcript_text(segments: list[TranscriptSegment]) -> str:
    """The transcript as plain text with times and speaker names, the form the notes engine reads."""
    lines = []
    for segment in segments:
        speaker = f"{segment.speaker_name}: " if segment.speaker_name else ""
        lines.append(f"[{_timestamp(segment.start_time)}] {speaker}{segment.text}")
    return "\n".join(lines)


async def make_notes(session_id: str, title: Optional[str] = None) -> LectureResult:
    session = get_session(session_id)
    text = transcript_text(sessions.get_segments(session_id))
    if not text:
        raise MeetingError("no_transcript", "This meeting session has no transcript yet.")
    return await run_in_threadpool(pipeline.text_to_notes, text, title or session.title)
