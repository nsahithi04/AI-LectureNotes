import subprocess

import pytest

from app.core import config


def upload(client, content, filename="lecture.mp4"):
    return client.post("/api/video/process", files={"video": (filename, content, "video/mp4")})


def error_code(response):
    return response.json()["error"]["code"]


@pytest.mark.parametrize("kind", ["mp4", "mov", "mkv"])
def test_valid_video_is_accepted(client, videos, temp_dir, kind):
    path = videos[kind]
    response = upload(client, path.read_bytes(), path.name)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["video"]["filename"] == path.name
    assert data["video"]["duration"] == pytest.approx(2, abs=0.2)
    assert data["transcription"]["text"] == "Hello."
    assert list(temp_dir.iterdir()) == []


def test_invalid_extension_is_rejected(client):
    response = upload(client, b"not a video", "lecture.exe")

    assert response.status_code == 415
    assert error_code(response) == "unsupported_file_type"


def test_empty_file_is_rejected(client, temp_dir):
    response = upload(client, b"")

    assert response.status_code == 400
    assert error_code(response) == "empty_file"
    assert list(temp_dir.iterdir()) == []


def test_oversized_file_is_rejected(client, monkeypatch, temp_dir):
    monkeypatch.setattr(config, "MAX_UPLOAD_SIZE_BYTES", 10)
    # Bypass the Content-Length check so this covers the limit applied while streaming.
    monkeypatch.setattr("app.main.MULTIPART_OVERHEAD_BYTES", 10_000)
    response = upload(client, b"x" * 100)

    assert response.status_code == 413
    assert error_code(response) == "file_too_large"
    assert list(temp_dir.iterdir()) == []


def test_oversized_request_is_rejected_before_reading_it(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_SIZE_BYTES", 10)
    monkeypatch.setattr("app.main.MULTIPART_OVERHEAD_BYTES", 0)
    response = upload(client, b"x" * 100)

    assert response.status_code == 413


def test_corrupted_video_is_rejected(client, temp_dir):
    response = upload(client, b"this is not really a video" * 100)

    assert response.status_code == 400
    assert error_code(response) == "invalid_video"
    assert list(temp_dir.iterdir()) == []


def test_truncated_video_is_rejected(client, videos, temp_dir):
    content = videos["mp4"].read_bytes()
    response = upload(client, content[: len(content) // 3])

    assert response.status_code == 400
    assert error_code(response) == "invalid_video"
    assert list(temp_dir.iterdir()) == []


def test_playlist_renamed_as_video_is_rejected(client):
    response = upload(client, b"#EXTM3U\n#EXTINF:1,\nhttp://127.0.0.1:9/secret\n")

    assert response.status_code == 400
    assert error_code(response) == "invalid_video"


def test_video_without_audio_is_rejected(client, videos, temp_dir):
    response = upload(client, videos["silent"].read_bytes())

    assert response.status_code == 422
    assert error_code(response) == "no_audio"
    assert list(temp_dir.iterdir()) == []


def test_video_over_the_time_limit_is_rejected(client, videos, monkeypatch, temp_dir):
    monkeypatch.setattr(config, "MAX_VIDEO_DURATION_SECONDS", 1)
    response = upload(client, videos["mp4"].read_bytes())

    assert response.status_code == 422
    assert error_code(response) == "video_too_long"
    assert list(temp_dir.iterdir()) == []


def test_filename_cannot_escape_the_temp_folder(client, videos, temp_dir):
    response = upload(client, videos["mp4"].read_bytes(), "../../evil.mp4")

    assert response.status_code == 200
    assert response.json()["data"]["video"]["filename"] == "evil.mp4"
    assert list(temp_dir.iterdir()) == []


def test_ffmpeg_failure_cleans_up_and_hides_details(client, videos, monkeypatch, temp_dir):
    failed = subprocess.CompletedProcess([], 1, "", "secret server path /Users/x")
    real_run = subprocess.run

    def fake_run(command, **kwargs):
        return failed if command[0] == "ffmpeg" else real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    response = upload(client, videos["mp4"].read_bytes())

    assert response.status_code == 500
    assert error_code(response) == "audio_extraction_failed"
    assert "secret" not in response.text
    assert list(temp_dir.iterdir()) == []


def test_missing_ffmpeg_gives_a_clear_error(client, videos, monkeypatch):
    def fake_run(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    response = upload(client, videos["mp4"].read_bytes())

    assert response.status_code == 503
    assert error_code(response) == "ffmpeg_missing"


def test_extracted_audio_is_16khz_mono(tmp_path, videos):
    from app.engine import audio_extractor

    output = tmp_path / "audio.wav"
    audio_extractor.extract_audio(videos["mp4"], "mov", output)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0", str(output)],
        capture_output=True, text=True, check=True,
    )
    assert probe.stdout.strip() == "16000,1"


def test_gaps_in_the_audio_track_keep_timestamps_in_line(tmp_path):
    from app.engine import audio_extractor

    once = tmp_path / "once.mp4"
    looped = tmp_path / "looped.mp4"
    output = tmp_path / "audio.wav"
    # 6 seconds of video with 2 seconds of audio, played twice: the audio has a 4 second gap.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=64x64:r=5:d=6", "-f", "lavfi", "-i", "sine=duration=2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(once)],
        check=True,
    )
    subprocess.run(["ffmpeg", "-v", "error", "-stream_loop", "1", "-i", str(once), "-c", "copy", str(looped)], check=True)

    audio_extractor.extract_audio(looped, "mov", output)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(output)],
        capture_output=True, text=True, check=True,
    )
    assert float(probe.stdout) == pytest.approx(8, abs=0.3)
