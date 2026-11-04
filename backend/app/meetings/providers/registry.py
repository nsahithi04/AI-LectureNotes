"""The meeting providers LectureAI knows about, and what each one supports."""

from typing import Optional

from app.meetings.errors import MeetingError
from app.meetings.providers.base import MeetingProvider, PlannedProvider
from app.meetings.schemas import Availability, Capability, ProcessingMode, ProviderId, ProviderInfo

# Built from each provider's current official documentation. See the README's meeting integrations section.
ZOOM = ProviderInfo(
    id=ProviderId.ZOOM,
    name="Zoom",
    availability=Availability.PLANNED,
    capabilities=[
        Capability.LIVE_TRANSCRIPT,
        Capability.LIVE_AUDIO,
        Capability.PARTICIPANTS,
        Capability.START_STOP_PROCESSING,
        Capability.WEBHOOKS,
    ],
    processing_modes=[ProcessingMode.LIVE],
    description="Live transcript and audio through Zoom Realtime Media Streams. Needs a paid Zoom plan with the Developer Pack.",
)

GOOGLE_MEET = ProviderInfo(
    id=ProviderId.GOOGLE_MEET,
    name="Google Meet",
    availability=Availability.PLANNED,
    capabilities=[
        Capability.MEETING_DETAILS,
        Capability.PARTICIPANTS,
        Capability.POST_MEETING_TRANSCRIPT,
    ],
    processing_modes=[ProcessingMode.POST_MEETING],
    description="Transcripts after the meeting through the Google Meet REST API. Someone must turn on transcription "
    "during the meeting, on a Workspace plan that includes it.",
)

MICROSOFT_TEAMS = ProviderInfo(
    id=ProviderId.MICROSOFT_TEAMS,
    name="Microsoft Teams",
    availability=Availability.PLANNED,
    capabilities=[Capability.MEETING_DETAILS, Capability.POST_MEETING_TRANSCRIPT],
    processing_modes=[ProcessingMode.POST_MEETING],
    description="Transcripts after the meeting through Microsoft Graph, once a tenant admin allows transcript access.",
)


class ProviderRegistry:
    def __init__(self, providers: list[MeetingProvider]):
        self._providers = {provider.info.id: provider for provider in providers}

    def get(self, provider_id: str) -> MeetingProvider:
        try:
            return self._providers[ProviderId(provider_id)]
        except (ValueError, KeyError):
            raise MeetingError("provider_not_found", f"Unknown meeting provider {provider_id!r}.") from None

    def list_info(self) -> list[ProviderInfo]:
        return [provider.info for provider in self._providers.values()]


def build_registry(google_meet: Optional[MeetingProvider] = None) -> ProviderRegistry:
    """Each built provider replaces its planned entry. Zoom and Teams are still planned."""
    return ProviderRegistry([PlannedProvider(ZOOM), google_meet or PlannedProvider(GOOGLE_MEET), PlannedProvider(MICROSOFT_TEAMS)])
