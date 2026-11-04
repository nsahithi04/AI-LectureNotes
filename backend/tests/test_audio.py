import pytest

from app.core import config


def upload(client, content, filename="lecture.mp3", **form):
    return client.post("/api/audio/process", files={"audio": (filename, content, "audio/mpeg")}, data=form)


def error_code(response):
    return response.json()["error"]["code"]


@pytest.mark.parametrize("kind", ["mp3", "wav", "m4a"])
def test_valid_audio_is_accepted(client, audios, temp_dir, kind):
    path = audios[kind]
    response = upload(client, path.read_bytes(), path.name)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"]["type"] == "audio"
    assert data["source"]["filename"] == path.name
    assert data["source"]["duration"] == pytest.approx(2, abs=0.2)
    assert data["transcription"]["text"] == "Hello."
    assert data["text"] == "Hello."
    assert list(temp_dir.iterdir()) == []


def test_video_file_is_rejected_as_audio(client, videos):
    response = upload(client, videos["mp4"].read_bytes(), "lecture.mp4")

    assert response.status_code == 415
    assert error_code(response) == "unsupported_file_type"


def test_corrupted_audio_is_rejected(client, temp_dir):
    response = upload(client, b"not really audio" * 100)

    assert response.status_code == 400
    assert error_code(response) == "invalid_audio"
    assert list(temp_dir.iterdir()) == []


def test_audio_over_the_time_limit_is_rejected(client, audios, monkeypatch, temp_dir):
    monkeypatch.setattr(config, "MAX_AUDIO_DURATION_SECONDS", 1)
    response = upload(client, audios["mp3"].read_bytes())

    assert response.status_code == 422
    assert error_code(response) == "audio_too_long"
    assert response.json()["error"]["message"] == "Audio recordings can be up to 0 minutes long."
    assert list(temp_dir.iterdir()) == []


def test_title_reaches_the_notes(client, audios):
    response = upload(client, audios["wav"].read_bytes(), "lecture.wav", title="Week 4")

    assert response.json()["data"]["lecture_notes"]["title"] == "Week 4"
