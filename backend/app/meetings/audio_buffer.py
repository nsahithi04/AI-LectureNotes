"""Collects live audio into fixed-length windows for our own transcription, without unbounded memory use."""

import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.meetings.events import AudioPacket

BYTES_PER_SAMPLE = 2  # 16-bit PCM


@dataclass(frozen=True)
class AudioWindow:
    start_ms: int
    pcm: bytes
    sample_rate: int
    channels: int

    @property
    def seconds(self) -> float:
        return len(self.pcm) / (self.sample_rate * self.channels * BYTES_PER_SAMPLE)

    def write_wav(self, path: Path) -> Path:
        with wave.open(str(path), "wb") as out:
            out.setnchannels(self.channels)
            out.setsampwidth(BYTES_PER_SAMPLE)
            out.setframerate(self.sample_rate)
            out.writeframes(self.pcm)
        return path


class AudioWindowBuffer:
    """Hands out a window every `window_seconds`. Never holds more than `max_buffered_seconds` of audio."""

    def __init__(self, window_seconds: float = 30, max_buffered_seconds: float = 120, min_window_seconds: float = 0.5):
        self.window_seconds = window_seconds
        self.max_buffered_seconds = max_buffered_seconds
        self.min_window_seconds = min_window_seconds
        self._buffer = bytearray()
        self._start_ms: Optional[int] = None
        self._format: Optional[tuple[int, int]] = None
        self.dropped_bytes = 0

    def _bytes_per_second(self) -> int:
        sample_rate, channels = self._format or (16_000, 1)
        return sample_rate * channels * BYTES_PER_SAMPLE

    def add(self, packet: AudioPacket) -> list[AudioWindow]:
        packet_format = (packet.sample_rate, packet.channels)
        windows = []
        if self._format and packet_format != self._format:
            # Never mix formats in one window.
            windows.extend(self.flush())
        self._format = packet_format
        if self._start_ms is None:
            self._start_ms = packet.timestamp_ms
        self._buffer.extend(packet.pcm)

        limit = int(self.max_buffered_seconds * self._bytes_per_second())
        if len(self._buffer) > limit:
            # Transcription has fallen behind: drop the oldest audio rather than run out of memory.
            excess = len(self._buffer) - limit
            excess -= excess % BYTES_PER_SAMPLE
            del self._buffer[:excess]
            self.dropped_bytes += excess
            self._start_ms += int(excess * 1000 / self._bytes_per_second())

        window_bytes = int(self.window_seconds * self._bytes_per_second())
        window_bytes -= window_bytes % BYTES_PER_SAMPLE
        while len(self._buffer) >= window_bytes:
            windows.append(self._take(window_bytes))
        return windows

    def _take(self, size: int) -> AudioWindow:
        sample_rate, channels = self._format or (16_000, 1)
        window = AudioWindow(self._start_ms or 0, bytes(self._buffer[:size]), sample_rate, channels)
        del self._buffer[:size]
        self._start_ms = (self._start_ms or 0) + int(size * 1000 / self._bytes_per_second())
        return window

    def flush(self) -> list[AudioWindow]:
        """Return whatever is left, if it's long enough to be worth transcribing."""
        if len(self._buffer) < self.min_window_seconds * self._bytes_per_second():
            self._buffer.clear()
            self._start_ms = None
            return []
        window = self._take(len(self._buffer))
        self._start_ms = None
        return [window]
