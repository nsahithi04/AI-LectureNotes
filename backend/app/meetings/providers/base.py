"""The interface every meeting provider implements.

Providers differ a lot: Zoom streams live transcripts, while Google Meet and Microsoft Teams only offer
transcripts after the meeting. Each provider declares its capabilities, and any method it doesn't
support raises a clear error instead of pretending to work.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping

from app.meetings.errors import MeetingError
from app.meetings.schemas import (
    Availability,
    Capability,
    MeetingDetails,
    MeetingSession,
    MeetingSummary,
    ProviderInfo,
    TranscriptSegment,
)


class WebhookResponse:
    """What to send back to the provider: a status code and an optional JSON body."""

    def __init__(self, status_code: int = 200, body: dict | None = None):
        self.status_code = status_code
        self.body = body


class MeetingProvider(ABC):
    @property
    @abstractmethod
    def info(self) -> ProviderInfo: ...

    def supports(self, capability: Capability) -> bool:
        return self.info.availability == Availability.AVAILABLE and capability in self.info.capabilities

    def _unsupported(self, action: str) -> MeetingError:
        if self.info.availability == Availability.PLANNED:
            return MeetingError("provider_not_available", f"{self.info.name} isn't available yet.")
        if self.info.availability == Availability.NOT_CONFIGURED:
            return MeetingError("provider_not_configured", f"{self.info.name} isn't set up on the server.")
        return MeetingError("capability_not_supported", f"{self.info.name} doesn't support {action}.")

    async def connect(self, user_id: str) -> str:
        """Start connecting the user's account. Returns the provider's sign-in URL."""
        raise self._unsupported("connecting an account")

    async def complete_connection(self, code: str, state: str) -> None:
        """Finish connecting, after the provider redirects back with an authorization code.

        The state identifies which user started signing in, so the callback never trusts anything else.
        """
        raise self._unsupported("connecting an account")

    async def disconnect(self, user_id: str) -> None:
        raise self._unsupported("disconnecting an account")

    async def list_meetings(self, user_id: str) -> list[MeetingSummary]:
        """The user's recent meetings, newest first, with whether each one has a transcript."""
        raise self._unsupported("listing meetings")

    async def get_meeting_details(self, user_id: str, provider_meeting_id: str) -> MeetingDetails:
        raise self._unsupported("meeting details")

    async def start_processing(self, session: MeetingSession) -> MeetingSession:
        raise self._unsupported("starting processing")

    async def stop_processing(self, session: MeetingSession) -> MeetingSession:
        raise self._unsupported("stopping processing")

    async def handle_webhook(self, headers: Mapping[str, str], body: bytes) -> WebhookResponse:
        raise self._unsupported("webhooks")

    async def retrieve_transcript(self, user_id: str, provider_meeting_id: str, session_id: str) -> list[TranscriptSegment]:
        """A finished meeting's transcript, as segments whose IDs start with session_id."""
        raise self._unsupported("transcripts after the meeting")


class PlannedProvider(MeetingProvider):
    """A provider that isn't built yet. It lists what it will support, so the UI can describe it honestly."""

    def __init__(self, info: ProviderInfo):
        self._info = info

    @property
    def info(self) -> ProviderInfo:
        return self._info
