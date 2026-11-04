"""Checking that a video or audio file can be processed.

The extension is only a first check. FFprobe then reads the file itself, so a renamed or damaged
file is rejected before any processing starts.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core import config
from app.engine.errors import EngineError
from app.engine.schemas import SourceInfo

logger = logging.getLogger(__name__)

# Each extension and the FFmpeg demuxer that must be able to read it. Naming the demuxer stops
# FFmpeg guessing a format from the file's content, such as a playlist that points to other URLs.
VIDEO_DEMUXERS = {".mp4": "mov", ".mov": "mov", ".mkv": "matroska"}
AUDIO_DEMUXERS = {".mp3": "mp3", ".wav": "wav", ".m4a": "mov"}

FFPROBE_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class MediaFile:
    filename: str  # cleaned-up original name, for display only
    path: Path
    size: int

    @property
    def demuxer(self) -> str:
        return {**VIDEO_DEMUXERS, **AUDIO_DEMUXERS}[self.path.suffix]


def _probe(media: MediaFile, error_code: str, kind: str) -> dict:
    command = [
        "ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", media.demuxer,
        "-print_format", "json", "-show_format", "-show_streams", str(media.path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        logger.error("ffprobe is not installed")
        raise EngineError("ffmpeg_missing", "Video and audio processing isn't available on the server.") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("ffprobe timed out on %s", media.filename)
        raise EngineError(error_code, f"This {kind} couldn't be read. It may be damaged.") from exc

    if result.returncode != 0:
        logger.warning("ffprobe rejected %s: %s", media.filename, result.stderr.strip())
        raise EngineError(error_code, f"This file isn't a valid {kind}, or it's damaged.")
    return json.loads(result.stdout)


def _duration(probe: dict, error_code: str, kind: str) -> float:
    try:
        duration = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EngineError(error_code, f"This {kind}'s length couldn't be read. It may be damaged.") from exc
    if duration <= 0:
        raise EngineError(error_code, f"This {kind}'s length couldn't be read. It may be damaged.")
    return duration


def inspect_video(video: MediaFile) -> SourceInfo:
    """Read the file with FFprobe and reject anything that can't be processed."""
    probe = _probe(video, "invalid_video", "video")
    streams = probe.get("streams", [])

    has_video = any(
        stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic")
        for stream in streams
    )
    if not has_video:
        raise EngineError("invalid_video", "This file doesn't contain a video stream.")
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise EngineError("no_audio", "This video has no audio, so there's nothing to transcribe.")

    duration = _duration(probe, "invalid_video", "video")
    if duration > config.MAX_VIDEO_DURATION_SECONDS:
        limit_minutes = config.MAX_VIDEO_DURATION_SECONDS // 60
        raise EngineError("video_too_long", f"Videos can be up to {limit_minutes} minutes long.")

    return SourceInfo(type="video", format=video.path.suffix.lstrip("."), filename=video.filename, size=video.size, duration=round(duration, 2))


def inspect_audio(audio: MediaFile) -> SourceInfo:
    """Read the file with FFprobe and reject anything that can't be processed."""
    probe = _probe(audio, "invalid_audio", "audio file")
    if not any(stream.get("codec_type") == "audio" for stream in probe.get("streams", [])):
        raise EngineError("invalid_audio", "This file doesn't contain any audio.")

    duration = _duration(probe, "invalid_audio", "audio file")
    if duration > config.MAX_AUDIO_DURATION_SECONDS:
        limit_minutes = config.MAX_AUDIO_DURATION_SECONDS // 60
        raise EngineError("audio_too_long", f"Audio recordings can be up to {limit_minutes} minutes long.")

    return SourceInfo(type="audio", format=audio.path.suffix.lstrip("."), filename=audio.filename, size=audio.size, duration=round(duration, 2))
