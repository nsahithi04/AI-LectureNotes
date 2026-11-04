"""The shared shapes every meeting provider is converted into.

Zoom, Google Meet and Microsoft Teams each describe meetings and transcripts differently. Provider code
turns their data into these models, so nothing after that point needs to know which provider it came from.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderId(str, Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"


class Capability(str, Enum):
    """What a provider can really do. Providers declare these instead of pretending to support everything."""

    LIVE_TRANSCRIPT = "live_transcript"            # transcript text while the meeting is running
    LIVE_AUDIO = "live_audio"                      # audio while the meeting is running
    POST_MEETING_TRANSCRIPT = "post_meeting_transcript"
    POST_MEETING_RECORDING = "post_meeting_recording"
    MEETING_DETAILS = "meeting_details"
    PARTICIPANTS = "participants"
    START_STOP_PROCESSING = "start_stop_processing"  # LectureAI can start or stop processing on request
    WEBHOOKS = "webhooks"                          # the provider tells us about meeting events


class ProcessingMode(str, Enum):
    LIVE = "live"
    POST_MEETING = "post_meeting"


class Availability(str, Enum):
    AVAILABLE = "available"            # built and configured
    NOT_CONFIGURED = "not_configured"  # built, but its credentials aren't set
    PLANNED = "planned"                # not built yet


class ProviderInfo(BaseModel):
    id: ProviderId
    name: str
    availability: Availability
    capabilities: list[Capability]
    processing_modes: list[ProcessingMode]
    description: str


class TranscriptionStrategy(str, Enum):
    PROVIDER = "provider"  # use the transcript the meeting platform sends
    OWN = "own"            # transcribe the platform's audio with our own Whisper service
    COMPARE = "compare"    # keep both, to compare accuracy later


class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"
    WAITING = "waiting"
    CONNECTING = "connecting"
    LIVE = "live"
    TRANSCRIBING = "transcribing"
    GENERATING_NOTES = "generating_notes"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


FINISHED_STATUSES = {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.STOPPED}


class Participant(BaseModel):
    id: str
    name: Optional[str] = None
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None


class MeetingSession(BaseModel):
    id: str
    provider: ProviderId
    provider_meeting_id: str
    title: Optional[str] = None
    organizer: Optional[str] = None
    status: SessionStatus = SessionStatus.WAITING
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    participants: list[Participant] = Field(default_factory=list)
    processing_mode: ProcessingMode
    transcription_strategy: TranscriptionStrategy = TranscriptionStrategy.PROVIDER
    error: Optional[str] = None


class TranscriptSegment(BaseModel):
    """One stretch of speech by one speaker, in the form the AI engine receives."""

    id: str
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    start_time: float  # seconds from the start of the meeting
    end_time: float
    text: str
    language: Optional[str] = None  # BCP 47 code, such as "en" or "en-US", when known
    source: str                     # where it came from, such as "zoom_rtms", "whisper" or "google_meet"
    # The provider's own timestamp in milliseconds since the epoch, kept so nothing is lost in conversion.
    source_timestamp_ms: Optional[int] = None


class TranscriptStatus(str, Enum):
    AVAILABLE = "available"    # ready to import
    PROCESSING = "processing"  # the meeting or its transcript hasn't finished yet
    NONE = "none"              # nobody turned on transcription, or the provider has deleted it


class MeetingSummary(BaseModel):
    """A past meeting in the teacher's list, before it's imported."""

    provider: ProviderId
    provider_meeting_id: str
    title: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    transcript_status: TranscriptStatus


class MeetingDetails(MeetingSummary):
    participants: list[Participant] = Field(default_factory=list)
