"""The engine's entry points: one for each kind of lecture source.

The engine only processes content. It must not import the web framework or know about users,
so any frontend, API or background worker can call it. These steps block while they work.
"""

from pathlib import Path
from typing import Optional

from app.engine import audio_extractor, document_reader, media_reader, notes_generator, transcriber
from app.engine.media_reader import MediaFile
from app.engine.schemas import LectureResult, SourceInfo


def _transcribe_to_notes(
    media: MediaFile,
    source: SourceInfo,
    work_dir: Path,
    title: Optional[str],
    language: Optional[str],
) -> LectureResult:
    audio_path = work_dir / "audio.wav"
    audio_extractor.extract_audio(media.path, media.demuxer, audio_path)
    transcript = transcriber.transcribe(audio_path, language)
    notes = notes_generator.generate_notes(transcript.text, title)
    source.characters = len(transcript.text)
    return LectureResult(source=source, transcription=transcript, text=transcript.text, lecture_notes=notes)


def video_to_notes(
    video: MediaFile,
    work_dir: Path,
    title: Optional[str] = None,
    language: Optional[str] = None,
) -> LectureResult:
    """Turn a video into a transcript and notes. Temporary files go in work_dir, which the caller removes."""
    return _transcribe_to_notes(video, media_reader.inspect_video(video), work_dir, title, language)


def audio_to_notes(
    audio: MediaFile,
    work_dir: Path,
    title: Optional[str] = None,
    language: Optional[str] = None,
) -> LectureResult:
    """Turn an audio recording into a transcript and notes. Temporary files go in work_dir."""
    return _transcribe_to_notes(audio, media_reader.inspect_audio(audio), work_dir, title, language)


def document_to_notes(path: Path, filename: str, size: int, title: Optional[str] = None) -> LectureResult:
    """Turn a PDF, Word or PowerPoint file with selectable text, such as slides or handouts, into notes."""
    source, text = document_reader.read_document(path, filename, size)
    notes = notes_generator.generate_notes(text, title)
    return LectureResult(source=source, text=text, lecture_notes=notes)


def text_to_notes(text: str, title: Optional[str] = None) -> LectureResult:
    """Turn pasted lecture text into notes."""
    text = text.strip()
    notes = notes_generator.generate_notes(text, title)
    return LectureResult(source=SourceInfo(type="text", characters=len(text)), text=text, lecture_notes=notes)
