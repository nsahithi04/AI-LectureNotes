"""HTTP endpoints for meeting integrations. They only read the request and call the meetings service.

There are no LectureAI logins yet, so every request acts as the one development user (DEV_USER_ID).

Connecting an account happens in the browser: the frontend sends the teacher to /{provider}/connect,
the provider asks them to sign in, and sends them back to /{provider}/callback, which returns them to
the frontend's Integrations page.
"""

from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core import config
from app.meetings.errors import MeetingError
from app.meetings.schemas import MeetingSession, MeetingSummary, ProviderInfo, TranscriptSegment
from app.schemas.meetings import Connection, MeetingResponse, NotesRequest
from app.schemas.process import ProcessResponse
from app.services import meetings_service

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.get("/providers", response_model=MeetingResponse[list[ProviderInfo]])
def list_providers() -> MeetingResponse[list[ProviderInfo]]:
    """Every meeting provider, whether it's available yet, and what it can do."""
    return MeetingResponse(data=meetings_service.registry.list_info())


@router.get("/connections", response_model=MeetingResponse[list[Connection]])
def list_connections() -> MeetingResponse[list[Connection]]:
    """Which providers the current user has connected, and with which account. Never includes tokens."""
    connections = []
    for info in meetings_service.registry.list_info():
        saved = meetings_service.tokens.get(info.id.value, config.DEV_USER_ID)
        connections.append(Connection(provider=info.id, connected=saved is not None, account=(saved or {}).get("account")))
    return MeetingResponse(data=connections)


@router.get("/sessions", response_model=MeetingResponse[list[MeetingSession]])
def list_sessions() -> MeetingResponse[list[MeetingSession]]:
    return MeetingResponse(data=meetings_service.sessions.all())


@router.get("/sessions/{session_id}", response_model=MeetingResponse[MeetingSession])
def get_session(session_id: str) -> MeetingResponse[MeetingSession]:
    return MeetingResponse(data=meetings_service.get_session(session_id))


@router.get("/sessions/{session_id}/transcript", response_model=MeetingResponse[list[TranscriptSegment]])
def get_transcript(session_id: str) -> MeetingResponse[list[TranscriptSegment]]:
    """The session's transcript, in time order."""
    meetings_service.get_session(session_id)
    return MeetingResponse(data=meetings_service.sessions.get_segments(session_id))


@router.post("/sessions/{session_id}/notes", response_model=ProcessResponse)
async def make_notes(session_id: str, request: Optional[NotesRequest] = None) -> ProcessResponse:
    """Turn an imported meeting's transcript into lecture notes, the same way pasted text is."""
    result = await meetings_service.make_notes(session_id, request.title if request else None)
    return ProcessResponse(message="Lecture notes generated successfully", data=result)


@router.get("/{provider_id}/connect")
async def connect(provider_id: str) -> RedirectResponse:
    """Send the teacher to the provider's sign-in page."""
    url = await meetings_service.registry.get(provider_id).connect(config.DEV_USER_ID)
    return RedirectResponse(url, status_code=302)


@router.get("/{provider_id}/callback")
async def callback(
    provider_id: str, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None
) -> RedirectResponse:
    """Where the provider sends the teacher back. Always returns them to the frontend, with the outcome."""
    provider = meetings_service.registry.get(provider_id)
    outcome = {"provider": provider.info.id.value}
    if error or not code:
        # The teacher cancelled, or the provider refused. Use up the state so it can't be replayed.
        try:
            meetings_service.states.consume(provider.info.id.value, state)
        except MeetingError:
            pass
        outcome["error"] = "access_denied" if error == "access_denied" else "invalid_connection"
    else:
        try:
            await provider.complete_connection(code, state)
            outcome["connected"] = "1"
        except MeetingError as exc:
            outcome["error"] = exc.code
    return RedirectResponse(f"{config.FRONTEND_URL}/integrations?{urlencode(outcome)}", status_code=302)


@router.post("/{provider_id}/disconnect", response_model=MeetingResponse[Connection])
async def disconnect(provider_id: str) -> MeetingResponse[Connection]:
    provider = meetings_service.registry.get(provider_id)
    await provider.disconnect(config.DEV_USER_ID)
    return MeetingResponse(data=Connection(provider=provider.info.id, connected=False))


@router.get("/{provider_id}/meetings", response_model=MeetingResponse[list[MeetingSummary]])
async def list_meetings(provider_id: str) -> MeetingResponse[list[MeetingSummary]]:
    """The teacher's recent meetings on this provider, newest first, with whether each has a transcript."""
    return MeetingResponse(data=await meetings_service.registry.get(provider_id).list_meetings(config.DEV_USER_ID))


@router.post("/{provider_id}/meetings/{meeting_id}/import", response_model=MeetingResponse[MeetingSession])
async def import_meeting(provider_id: str, meeting_id: str) -> MeetingResponse[MeetingSession]:
    """Copy a finished meeting's transcript into LectureAI, ready to make notes from."""
    return MeetingResponse(data=await meetings_service.import_meeting(provider_id, meeting_id, config.DEV_USER_ID))
