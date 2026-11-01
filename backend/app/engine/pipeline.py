"""The engine's entry point: runs the processing steps in order.

The engine only processes content. It must not import the web framework or know about users,
so any frontend, API or background worker can call it. These steps block while they work.
"""

from pathlib import Path
from typing import Optional

from app.engine import audio_extractor, notes_generator, transcriber, video_reader
from app.engine.schemas import LectureResult
from app.engine.video_reader import VideoFile


def video_to_notes(
    video: VideoFile,
    work_dir: Path,
    title: Optional[str] = None,
    language: Optional[str] = None,
) -> LectureResult:
    """Turn a video into a transcript and notes. Temporary files go in work_dir, which the caller removes."""
    video_info = video_reader.inspect_video(video)
    audio_path = work_dir / "audio.wav"
    audio_extractor.extract_audio(video.path, video.demuxer, audio_path)
    transcript = transcriber.transcribe(audio_path, language)
    notes = notes_generator.generate_notes(transcript.text, title)
    return LectureResult(video=video_info, transcription=transcript, lecture_notes=notes)
