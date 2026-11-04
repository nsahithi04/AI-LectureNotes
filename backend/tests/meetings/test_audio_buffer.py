import struct
import wave

from app.meetings.audio_buffer import AudioWindowBuffer
from app.meetings.events import AudioPacket

START = 1_727_384_000_000


def packet(seconds, at_ms=START, sample_rate=16_000, value=0):
    return AudioPacket(None, at_ms, struct.pack("<h", value) * int(sample_rate * seconds), sample_rate)


def test_windows_have_the_right_length_and_start_time():
    buffer = AudioWindowBuffer(window_seconds=2)
    windows = []
    for n in range(5):
        windows += buffer.add(packet(1, at_ms=START + n * 1000))

    assert [w.seconds for w in windows] == [2, 2]
    assert [w.start_ms for w in windows] == [START, START + 2000]


def test_memory_is_capped_by_dropping_the_oldest_audio():
    buffer = AudioWindowBuffer(window_seconds=100, max_buffered_seconds=3)
    buffer.add(packet(5))

    [window] = buffer.flush()
    assert window.seconds == 3
    assert window.start_ms == START + 2000
    assert buffer.dropped_bytes == 2 * 16_000 * 2


def test_tiny_leftovers_are_not_worth_transcribing():
    buffer = AudioWindowBuffer(window_seconds=10, min_window_seconds=0.5)
    buffer.add(packet(0.2))

    assert buffer.flush() == []


def test_a_change_of_audio_format_starts_a_new_window():
    buffer = AudioWindowBuffer(window_seconds=10)
    buffer.add(packet(1))
    [old_format] = buffer.add(packet(1, sample_rate=8_000))

    assert (old_format.sample_rate, old_format.seconds) == (16_000, 1)


def test_windows_can_be_saved_as_wav_for_whisper(tmp_path):
    [window] = AudioWindowBuffer(window_seconds=1).add(packet(1, value=1000))
    path = window.write_wav(tmp_path / "window.wav")

    with wave.open(str(path)) as audio:
        assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getnframes()) == (16_000, 1, 2, 16_000)
