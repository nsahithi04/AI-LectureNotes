from types import SimpleNamespace

import pytest

from app.engine.errors import EngineError
from app.engine import transcriber


class FakeModel:
    supported_languages = ["en", "hi"]

    def __init__(self, segments=(), error=None):
        self.segments = segments
        self.error = error
        self.language = "unset"

    def transcribe(self, path, language=None, vad_filter=False):
        self.language = language

        def generate():
            if self.error:
                raise self.error
            yield from self.segments

        return generate(), SimpleNamespace(language=language or "en")


@pytest.fixture
def real_transcribe(monkeypatch, fake_transcription):
    monkeypatch.undo()
    monkeypatch.setattr(transcriber, "_model", None)
    return transcriber.transcribe


def use_model(monkeypatch, model):
    monkeypatch.setattr(transcriber, "get_model", lambda: model)


def segment(start, end, text):
    return SimpleNamespace(start=start, end=end, text=text)


def test_segments_keep_their_order_and_timestamps(real_transcribe, monkeypatch):
    use_model(monkeypatch, FakeModel([segment(0.0, 8.5, " Welcome. "), segment(8.5, 12.123, " Today we start. ")]))

    transcript = real_transcribe("audio.wav")

    assert transcript.language == "en"
    assert transcript.text == "Welcome. Today we start."
    assert [(s.start, s.end, s.text) for s in transcript.segments] == [(0.0, 8.5, "Welcome."), (8.5, 12.12, "Today we start.")]


def test_language_is_passed_to_whisper(real_transcribe, monkeypatch):
    model = FakeModel([segment(0, 1, "Namaste")])
    use_model(monkeypatch, model)

    transcript = real_transcribe("audio.wav", "hi")

    assert model.language == "hi"
    assert transcript.language == "hi"


def test_blank_language_means_auto_detect(real_transcribe, monkeypatch):
    model = FakeModel([segment(0, 1, "Hello")])
    use_model(monkeypatch, model)

    real_transcribe("audio.wav", "")

    assert model.language is None


def test_unsupported_language_is_rejected(real_transcribe, monkeypatch):
    use_model(monkeypatch, FakeModel())

    with pytest.raises(EngineError) as error:
        real_transcribe("audio.wav", "klingon")

    assert error.value.code == "unsupported_language"


def test_empty_transcript_is_rejected(real_transcribe, monkeypatch):
    use_model(monkeypatch, FakeModel([segment(0, 1, "   ")]))

    with pytest.raises(EngineError) as error:
        real_transcribe("audio.wav")

    assert error.value.code == "empty_transcript"


def test_failure_while_reading_segments_is_handled(real_transcribe, monkeypatch):
    use_model(monkeypatch, FakeModel(error=RuntimeError("private model path")))

    with pytest.raises(EngineError) as error:
        real_transcribe("audio.wav")

    assert error.value.code == "transcription_failed"
    assert "private" not in error.value.message


def test_model_load_failure_is_handled(real_transcribe, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("download failed")

    monkeypatch.setattr(transcriber, "WhisperModel", fail)

    with pytest.raises(EngineError) as error:
        real_transcribe("audio.wav")

    assert error.value.code == "whisper_unavailable"


def test_model_is_only_loaded_once(real_transcribe, monkeypatch):
    loads = []
    monkeypatch.setattr(transcriber, "WhisperModel", lambda *args, **kwargs: loads.append(1) or FakeModel())

    transcriber.get_model()
    transcriber.get_model()

    assert len(loads) == 1


def test_transcription_failure_cleans_up_temp_files(client, videos, monkeypatch, temp_dir):
    def fail(audio_path, language=None):
        raise EngineError("transcription_failed", "The lecture couldn't be transcribed.")

    monkeypatch.setattr(transcriber, "transcribe", fail)
    response = client.post("/api/video/process", files={"video": ("a.mp4", videos["mp4"].read_bytes(), "video/mp4")})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "transcription_failed"
    assert list(temp_dir.iterdir()) == []
