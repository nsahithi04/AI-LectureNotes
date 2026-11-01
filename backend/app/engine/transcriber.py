"""Speech-to-text with faster-whisper. The model loads once, then is reused for every video."""

import logging
import threading
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

from app.core import config
from app.engine.errors import EngineError
from app.engine.schemas import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)

_model: Optional[WhisperModel] = None
_model_lock = threading.Lock()


def get_model() -> WhisperModel:
    global _model
    with _model_lock:
        if _model is None:
            try:
                logger.info("Loading Whisper model %r", config.WHISPER_MODEL)
                _model = WhisperModel(
                    config.WHISPER_MODEL,
                    device=config.WHISPER_DEVICE,
                    compute_type=config.WHISPER_COMPUTE_TYPE,
                )
            except Exception as exc:
                logger.exception("Could not load Whisper model %r", config.WHISPER_MODEL)
                raise EngineError("whisper_unavailable", "Transcription isn't available on the server.") from exc
        return _model


def transcribe(audio_path: Path, language: Optional[str] = None) -> Transcript:
    """Transcribe an audio file. With no language given, Whisper detects it."""
    model = get_model()
    language = (language or "").strip().lower()

    if language and language not in model.supported_languages:
        raise EngineError("unsupported_language", f"Language {language!r} isn't supported. Use a code such as en or hi.")

    try:
        # Segments are generated lazily: the real work happens in the loop below.
        segments, info = model.transcribe(str(audio_path), language=language or None, vad_filter=True)
        transcript_segments = [
            TranscriptSegment(start=round(segment.start, 2), end=round(segment.end, 2), text=segment.text.strip())
            for segment in segments
            if segment.text.strip()
        ]
    except Exception as exc:
        logger.exception("Transcription failed")
        raise EngineError("transcription_failed", "The lecture couldn't be transcribed.") from exc

    if not transcript_segments:
        raise EngineError("empty_transcript", "No speech was found in this video.")

    return Transcript(
        language=info.language,
        text=" ".join(segment.text for segment in transcript_segments),
        segments=transcript_segments,
    )
