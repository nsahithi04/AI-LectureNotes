"""Turns raw transcript events from any provider into TranscriptSegments.

It keeps speaker attribution and the provider's timestamps, converts times to seconds from the start of
the meeting, joins fragments of the same unfinished sentence, and drops repeats of text it has just seen.
"""

import re
from collections import deque
from typing import Optional

from app.meetings.events import TranscriptEvent
from app.meetings.schemas import TranscriptSegment

SENTENCE_END = re.compile(r"[.!?…。！？][\"')\]]*$")


def ends_sentence(text: str) -> bool:
    return bool(SENTENCE_END.search(text.strip()))


def _comparable(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


class TranscriptNormalizer:
    def __init__(
        self,
        session_id: str,
        meeting_start_ms: Optional[int] = None,
        max_gap_ms: int = 1500,
        max_segment_chars: int = 600,
        duplicate_window_ms: int = 5000,
    ):
        self.session_id = session_id
        self.meeting_start_ms = meeting_start_ms
        self.max_gap_ms = max_gap_ms
        self.max_segment_chars = max_segment_chars
        self.duplicate_window_ms = duplicate_window_ms
        self._participants: dict[str, str] = {}
        self._unnamed: dict[str, str] = {}
        self._open: Optional[dict] = None
        self._recent: deque[tuple[Optional[str], str, int]] = deque(maxlen=100)
        self._count = 0

    def set_participant(self, participant_id: str, name: Optional[str]) -> None:
        if name:
            self._participants[participant_id] = name

    def _speaker_name(self, speaker_id: Optional[str], name: Optional[str]) -> Optional[str]:
        if name:
            if speaker_id:
                self._participants.setdefault(speaker_id, name)
            return name
        if speaker_id is None:
            return None
        if speaker_id in self._participants:
            return self._participants[speaker_id]
        # A stable placeholder, so the same unnamed person keeps the same label.
        return self._unnamed.setdefault(speaker_id, f"Speaker {len(self._unnamed) + 1}")

    def _seconds(self, ms: int) -> float:
        if self.meeting_start_ms is None:
            self.meeting_start_ms = ms
        return round(max(0, ms - self.meeting_start_ms) / 1000, 3)

    def _is_duplicate(self, event: TranscriptEvent, text: str) -> bool:
        key = _comparable(text)
        for speaker_id, seen, start_ms in self._recent:
            if speaker_id == event.speaker_id and seen == key and abs(start_ms - event.start_ms) <= self.duplicate_window_ms:
                return True
        self._recent.append((event.speaker_id, key, event.start_ms))
        return False

    def _close(self) -> Optional[TranscriptSegment]:
        if self._open is None:
            return None
        current, self._open = self._open, None
        self._count += 1
        start = self._seconds(current["start_ms"])
        return TranscriptSegment(
            id=f"{self.session_id}-{self._count:05d}",
            speaker_id=current["speaker_id"],
            speaker_name=current["speaker_name"],
            start_time=start,
            end_time=max(start, self._seconds(current["end_ms"])),
            text=current["text"],
            language=current["language"],
            source=current["source"],
            source_timestamp_ms=current["start_ms"],
        )

    def add(self, event: TranscriptEvent) -> list[TranscriptSegment]:
        """Add one event. Returns the segments that are now complete."""
        text = " ".join(event.text.split())
        if not text or self._is_duplicate(event, text):
            return []

        end_ms = max(event.end_ms or event.start_ms, event.start_ms)
        current = self._open
        if (
            current is not None
            and current["speaker_id"] == event.speaker_id
            and current["source"] == event.source
            and not ends_sentence(current["text"])
            and 0 <= event.start_ms - current["end_ms"] <= self.max_gap_ms
            and len(current["text"]) + len(text) < self.max_segment_chars
        ):
            # The same speaker carrying on an unfinished sentence.
            current["text"] = f"{current['text']} {text}"
            current["end_ms"] = max(current["end_ms"], end_ms)
            return []

        closed = self._close()
        self._open = {
            "speaker_id": event.speaker_id,
            "speaker_name": self._speaker_name(event.speaker_id, event.speaker_name),
            "start_ms": event.start_ms,
            "end_ms": end_ms,
            "text": text,
            "language": event.language,
            "source": event.source,
        }
        return [closed] if closed else []

    def flush_if_idle(self, now_ms: int, idle_ms: int = 4000) -> list[TranscriptSegment]:
        """Close an unfinished sentence when its speaker has gone quiet, so it doesn't wait forever."""
        if self._open is not None and now_ms - self._open["end_ms"] >= idle_ms:
            return [self._close()]
        return []

    def flush(self) -> list[TranscriptSegment]:
        closed = self._close()
        return [closed] if closed else []
