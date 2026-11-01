"""Checking that a video can be processed.

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
from app.engine.schemas import VideoInfo

logger = logging.getLogger(__name__)

# Each extension and the FFmpeg demuxer that must be able to read it. Naming the demuxer stops
# FFmpeg guessing a format from the file's content, such as a playlist that points to other URLs.
DEMUXERS = {".mp4": "mov", ".mov": "mov", ".mkv": "matroska"}

FFPROBE_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class VideoFile:
    filename: str  # cleaned-up original name, for display only
    path: Path
    size: int

    @property
    def demuxer(self) -> str:
        return DEMUXERS[self.path.suffix]


def _probe(video: VideoFile) -> dict:
    command = [
        "ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", video.demuxer,
        "-print_format", "json", "-show_format", "-show_streams", str(video.path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        logger.error("ffprobe is not installed")
        raise EngineError("ffmpeg_missing", "Video processing isn't available on the server.") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("ffprobe timed out on %s", video.filename)
        raise EngineError("invalid_video", "This video couldn't be read. It may be damaged.") from exc

    if result.returncode != 0:
        logger.warning("ffprobe rejected %s: %s", video.filename, result.stderr.strip())
        raise EngineError("invalid_video", "This file isn't a valid video, or it's damaged.")
    return json.loads(result.stdout)


def inspect_video(video: VideoFile) -> VideoInfo:
    """Read the file with FFprobe and reject anything that can't be processed."""
    probe = _probe(video)
    streams = probe.get("streams", [])

    has_video = any(
        stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic")
        for stream in streams
    )
    if not has_video:
        raise EngineError("invalid_video", "This file doesn't contain a video stream.")
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise EngineError("no_audio", "This video has no audio, so there's nothing to transcribe.")

    try:
        duration = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EngineError("invalid_video", "This video's length couldn't be read. It may be damaged.") from exc
    if duration <= 0:
        raise EngineError("invalid_video", "This video's length couldn't be read. It may be damaged.")

    if duration > config.MAX_VIDEO_DURATION_SECONDS:
        limit_minutes = config.MAX_VIDEO_DURATION_SECONDS // 60
        raise EngineError("video_too_long", f"Videos can be up to {limit_minutes} minutes long.")

    return VideoInfo(filename=video.filename, duration=round(duration, 2), size=video.size)
