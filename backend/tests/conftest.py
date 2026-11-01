import subprocess

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.engine.schemas import GeneratedNotes, Transcript, TranscriptSegment
from app.engine import notes_generator, transcriber


@pytest.fixture(autouse=True)
def temp_dir(tmp_path, monkeypatch):
    """Point TEMP_DIR at an empty folder so each test can check what was left behind."""
    folder = tmp_path / "temp"
    monkeypatch.setattr(config, "TEMP_DIR", folder)
    return folder


@pytest.fixture(autouse=True)
def fake_transcription(monkeypatch):
    """Tests never run the real model. Whisper's own behaviour is tested with a fake in test_transcription.py."""
    transcript = Transcript(language="en", text="Hello.", segments=[TranscriptSegment(start=0, end=1, text="Hello.")])
    monkeypatch.setattr(transcriber, "transcribe", lambda audio_path, language=None: transcript)


@pytest.fixture(autouse=True)
def fake_notes(monkeypatch):
    """Tests never call Gemini. The notes service is tested with a fake client in test_notes.py."""
    real_generate_notes = notes_generator.generate_notes

    def generate_notes(transcript, title=None):
        return GeneratedNotes(
            title=title or "Generated title",
            overview="Overview.",
            learning_objectives=[],
            sections=[{"heading": "Topic", "content": transcript, "key_points": [], "definitions": [], "examples": []}],
            important_concepts=[],
            key_takeaways=[],
            conclusion="Conclusion.",
        )

    monkeypatch.setattr(notes_generator, "generate_notes", generate_notes)
    return real_generate_notes


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def make_video(path, audio=True):
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=64x64:r=5:d=2"]
    if audio:
        command += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        command += ["-c:a", "aac"]
    subprocess.run([*command, str(path)], check=True)
    return path


@pytest.fixture(scope="session")
def videos(tmp_path_factory):
    folder = tmp_path_factory.mktemp("videos")
    return {
        "mp4": make_video(folder / "lecture.mp4"),
        "mov": make_video(folder / "lecture.mov"),
        "mkv": make_video(folder / "lecture.mkv"),
        "silent": make_video(folder / "silent.mp4", audio=False),
    }
