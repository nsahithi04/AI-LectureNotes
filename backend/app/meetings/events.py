"""Raw events from a provider, after its own format has been decoded but before normalization.

Provider code produces these. Times are milliseconds since the epoch, as meeting platforms send them.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class TranscriptEvent:
    speaker_id: Optional[str]
    speaker_name: Optional[str]
    start_ms: int
    end_ms: Optional[int]
    text: str
    language: Optional[str]
    source: str
    # The provider's own ID for this event, when it has one. Used to drop exact duplicates.
    event_id: Optional[str] = None


@dataclass(frozen=True)
class AudioPacket:
    speaker_id: Optional[str]  # None for audio of the whole meeting mixed together
    timestamp_ms: int
    pcm: bytes                 # 16-bit little-endian PCM
    sample_rate: int = 16_000
    channels: int = 1


class ParticipantAction(str, Enum):
    JOINED = "joined"
    LEFT = "left"


@dataclass(frozen=True)
class ParticipantEvent:
    action: ParticipantAction
    participant_id: str
    name: Optional[str]
    timestamp_ms: int
