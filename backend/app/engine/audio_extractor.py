"""Extracting a video's audio with FFmpeg, in the format Whisper expects."""

import logging
import subprocess
from pathlib import Path

from app.engine.errors import EngineError
from app.engine.schemas import AudioInfo

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHANNELS = 1
FFMPEG_TIMEOUT_SECONDS = 600


def extract_audio(video_path: Path, demuxer: str, output_path: Path) -> AudioInfo:
    """Write the first audio track to output_path as 16 kHz mono WAV."""
    # An argument list, not a shell string, so nothing in a path can run as a command.
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", demuxer,
        "-i", str(video_path), "-map", "0:a:0", "-vn",
        # Fill gaps in the audio track with silence, so transcript timestamps match the video.
        "-af", "aresample=async=1:first_pts=0",
        "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(output_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        logger.error("ffmpeg is not installed")
        raise EngineError("ffmpeg_missing", "Video processing isn't available on the server.") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("ffmpeg timed out on %s", video_path.name)
        raise EngineError("audio_extraction_failed", "Extracting the audio took too long.") from exc

    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        logger.error("ffmpeg failed with code %s: %s", result.returncode, result.stderr.strip())
        raise EngineError("audio_extraction_failed", "The audio couldn't be extracted from this video.")

    return AudioInfo(sample_rate=SAMPLE_RATE, channels=CHANNELS, size=output_path.stat().st_size)
