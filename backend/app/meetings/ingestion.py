"""Receives a session's live events and passes them on in order, without duplicates.

Transcript events are held briefly so ones that arrive out of order can be put back in order. Every
buffer has a size limit, so a long or noisy meeting can't use unlimited memory.
"""

import heapq
import itertools
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Optional

from app.meetings.audio_buffer import AudioWindow, AudioWindowBuffer
from app.meetings.events import AudioPacket, ParticipantAction, ParticipantEvent, TranscriptEvent
from app.meetings.normalizer import TranscriptNormalizer
from app.meetings.schemas import Participant, TranscriptionStrategy, TranscriptSegment


def _time(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class IngestionService:
    def __init__(
        self,
        normalizer: TranscriptNormalizer,
        strategy: TranscriptionStrategy = TranscriptionStrategy.PROVIDER,
        on_segments: Optional[Callable[[list[TranscriptSegment]], None]] = None,
        audio_buffer: Optional[AudioWindowBuffer] = None,
        reorder_window_ms: int = 2000,
        max_pending: int = 1000,
        dedupe_capacity: int = 5000,
    ):
        self.normalizer = normalizer
        self.strategy = strategy
        self.on_segments = on_segments
        self.audio_buffer = audio_buffer or AudioWindowBuffer()
        self.reorder_window_ms = reorder_window_ms
        self.max_pending = max_pending
        self.dedupe_capacity = dedupe_capacity
        self.participants: dict[str, Participant] = {}
        self._pending: list[tuple[int, int, TranscriptEvent]] = []
        self._order = itertools.count()
        self._seen: OrderedDict[tuple, None] = OrderedDict()
        self._latest_ms: Optional[int] = None
        self._released_ms: Optional[int] = None
        self.duplicates_dropped = 0
        self.late_events = 0

    @property
    def uses_provider_transcript(self) -> bool:
        return self.strategy in (TranscriptionStrategy.PROVIDER, TranscriptionStrategy.COMPARE)

    @property
    def uses_audio(self) -> bool:
        return self.strategy in (TranscriptionStrategy.OWN, TranscriptionStrategy.COMPARE)

    def _is_duplicate(self, event: TranscriptEvent) -> bool:
        key = ("id", event.event_id) if event.event_id else ("content", event.speaker_id, event.start_ms, event.text.strip())
        if key in self._seen:
            self.duplicates_dropped += 1
            return True
        self._seen[key] = None
        if len(self._seen) > self.dedupe_capacity:
            self._seen.popitem(last=False)
        return False

    def _emit(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        if segments and self.on_segments:
            self.on_segments(segments)
        return segments

    def _release(self, until_ms: Optional[int]) -> list[TranscriptSegment]:
        segments = []
        while self._pending and (until_ms is None or self._pending[0][0] <= until_ms or len(self._pending) > self.max_pending):
            start_ms, _, event = heapq.heappop(self._pending)
            self._released_ms = max(self._released_ms or start_ms, start_ms)
            segments.extend(self.normalizer.add(event))
        return segments

    def add_transcript(self, event: TranscriptEvent) -> list[TranscriptSegment]:
        """Add a transcript event. Returns the segments completed as a result."""
        if not self.uses_provider_transcript or self._is_duplicate(event):
            return []
        if self._released_ms is not None and event.start_ms < self._released_ms:
            # Too late to put back in order. Keep it rather than lose speech; segments are sorted when read.
            self.late_events += 1
        heapq.heappush(self._pending, (event.start_ms, next(self._order), event))
        self._latest_ms = max(self._latest_ms or event.start_ms, event.start_ms)
        return self._emit(self._release(self._latest_ms - self.reorder_window_ms))

    def add_participant(self, event: ParticipantEvent) -> None:
        participant = self.participants.get(event.participant_id) or Participant(id=event.participant_id)
        if event.name:
            participant.name = event.name
            self.normalizer.set_participant(event.participant_id, event.name)
        if event.action == ParticipantAction.JOINED:
            participant.joined_at = participant.joined_at or _time(event.timestamp_ms)
            participant.left_at = None
        else:
            participant.left_at = _time(event.timestamp_ms)
        self.participants[event.participant_id] = participant

    def add_audio(self, packet: AudioPacket) -> list[AudioWindow]:
        """Add an audio packet. Returns windows ready for our own transcription, if that's in use."""
        # Only the mixed meeting audio is transcribed, so each person's speech is transcribed once.
        if not self.uses_audio or packet.speaker_id is not None:
            return []
        return self.audio_buffer.add(packet)

    def tick(self, now_ms: int) -> list[TranscriptSegment]:
        """Call regularly: releases held events and closes sentences whose speaker has gone quiet."""
        segments = self._release(now_ms - self.reorder_window_ms)
        segments.extend(self.normalizer.flush_if_idle(now_ms))
        return self._emit(segments)

    def finish(self) -> tuple[list[TranscriptSegment], list[AudioWindow]]:
        """Call when the meeting ends: returns everything still held."""
        segments = self._release(None)
        segments.extend(self.normalizer.flush())
        windows = self.audio_buffer.flush() if self.uses_audio else []
        return self._emit(segments), windows
