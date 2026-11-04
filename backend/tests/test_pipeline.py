from app.engine.errors import EngineError
from app.engine import notes_generator, transcriber


def process(client, videos, **form):
    files = {"video": ("lecture.mp4", videos["mp4"].read_bytes(), "video/mp4")}
    return client.post("/api/video/process", files=files, data=form)


def test_full_response_has_video_transcript_and_notes(client, videos, temp_dir):
    response = process(client, videos)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Lecture notes generated successfully"
    assert body["data"]["source"]["filename"] == "lecture.mp4"
    assert body["data"]["transcription"]["segments"][0]["text"] == "Hello."
    assert body["data"]["lecture_notes"]["title"] == "Generated title"
    assert list(temp_dir.iterdir()) == []


def test_notes_are_generated_from_the_transcript(client, videos):
    response = process(client, videos)

    assert response.json()["data"]["lecture_notes"]["sections"][0]["content"] == "Hello."


def test_title_reaches_the_notes(client, videos):
    response = process(client, videos, title="Week 3")

    assert response.json()["data"]["lecture_notes"]["title"] == "Week 3"


def test_language_reaches_transcription(client, videos, monkeypatch):
    real_transcribe = transcriber.transcribe
    languages = []

    def transcribe(audio_path, language=None):
        languages.append(language)
        return real_transcribe(audio_path, language)

    monkeypatch.setattr(transcriber, "transcribe", transcribe)
    process(client, videos, language="hi")

    assert languages == ["hi"]


def test_notes_failure_returns_no_partial_result_and_cleans_up(client, videos, monkeypatch, temp_dir):
    def fail(transcript, title=None):
        raise EngineError("gemini_rate_limited", "The AI service has reached its usage limit. Try again later.")

    monkeypatch.setattr(notes_generator, "generate_notes", fail)
    response = process(client, videos)

    assert response.status_code == 429
    assert response.json() == {
        "success": False,
        "error": {
            "code": "gemini_rate_limited",
            "message": "The AI service has reached its usage limit. Try again later.",
        },
    }
    assert list(temp_dir.iterdir()) == []


def test_unexpected_failure_hides_details_and_cleans_up(client, videos, monkeypatch, temp_dir):
    def fail(transcript, title=None):
        raise RuntimeError("private server detail")

    monkeypatch.setattr(notes_generator, "generate_notes", fail)
    response = process(client, videos)

    assert response.status_code == 500
    assert "private" not in response.text
    assert list(temp_dir.iterdir()) == []
