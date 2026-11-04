import struct

from app.meetings.audio_buffer import AudioWindowBuffer
from app.meetings.events import AudioPacket, ParticipantAction, ParticipantEvent, TranscriptEvent
from app.meetings.ingestion import IngestionService
from app.meetings.normalizer import TranscriptNormalizer
from app.meetings.schemas import TranscriptionStrategy
from tests.meetings.conftest import MEETING_START


def event(text, start_s, speaker="1", event_id=None):
    start = MEETING_START + int(start_s * 1000)
    return TranscriptEvent(speaker, None, start, start + 900, text, "en", "zoom_rtms", event_id)


def service(strategy=TranscriptionStrategy.PROVIDER, **kwargs):
    received = []
    ingestion = IngestionService(
        TranscriptNormalizer("s1", MEETING_START),
        strategy=strategy,
        on_segments=received.extend,
        **kwargs,
    )
    return ingestion, received


def silence(seconds, speaker=None, at_s=0):
    pcm = struct.pack("<h", 0) * int(16_000 * seconds)
    return AudioPacket(speaker, MEETING_START + int(at_s * 1000), pcm)


def test_out_of_order_events_are_put_back_in_order():
    ingestion, received = service(reorder_window_ms=3000)
    for text, start in [("One.", 1), ("Three.", 3), ("Two.", 2), ("Four.", 4)]:
        ingestion.add_transcript(event(text, start))
    ingestion.finish()

    assert [s.text for s in received] == ["One.", "Two.", "Three.", "Four."]
    assert ingestion.late_events == 0


def test_events_too_late_to_reorder_are_still_kept_and_counted():
    ingestion, received = service(reorder_window_ms=1000)
    for text, start in [("One.", 1), ("Five.", 5), ("Nine.", 9), ("Two.", 2)]:
        ingestion.add_transcript(event(text, start))
    ingestion.finish()

    assert sorted(s.text for s in received) == ["Five.", "Nine.", "One.", "Two."]
    assert ingestion.late_events == 1


def test_duplicate_events_are_dropped_by_id_and_by_content():
    ingestion, received = service()
    ingestion.add_transcript(event("Hello.", 1, event_id="a"))
    ingestion.add_transcript(event("Hello again.", 3, event_id="a"))  # same ID, resent
    ingestion.add_transcript(event("Goodbye.", 5))
    ingestion.add_transcript(event("Goodbye.", 5))  # same content, no ID
    ingestion.finish()

    assert [s.text for s in received] == ["Hello.", "Goodbye."]
    assert ingestion.duplicates_dropped == 2


def test_waiting_events_are_capped():
    ingestion, received = service(reorder_window_ms=10_000_000, max_pending=3)
    for n in range(10):
        ingestion.add_transcript(event(f"Sentence {n}.", n, speaker=str(n)))

    # Most were released early instead of piling up, and nothing was lost.
    assert len(ingestion._pending) <= 3
    ingestion.finish()
    assert len(received) == 10


def test_tick_releases_held_events_and_quiet_sentences():
    ingestion, received = service(reorder_window_ms=2000)
    ingestion.add_transcript(event("and then the model", 1))

    ingestion.tick(MEETING_START + 2_000)
    assert received == []
    ingestion.tick(MEETING_START + 10_000)
    assert [s.text for s in received] == ["and then the model"]


def test_participant_names_reach_the_transcript_and_join_and_leave_times_are_kept():
    ingestion, received = service()
    ingestion.add_participant(ParticipantEvent(ParticipantAction.JOINED, "1", "Dr. Rao", MEETING_START))
    ingestion.add_transcript(event("Welcome.", 1))
    ingestion.add_participant(ParticipantEvent(ParticipantAction.LEFT, "1", None, MEETING_START + 60_000))
    ingestion.finish()

    assert received[0].speaker_name == "Dr. Rao"
    participant = ingestion.participants["1"]
    assert participant.name == "Dr. Rao"
    assert participant.left_at.timestamp() * 1000 == MEETING_START + 60_000


def test_provider_strategy_ignores_audio_so_nothing_is_transcribed_twice():
    ingestion, _ = service(TranscriptionStrategy.PROVIDER)

    assert ingestion.add_audio(silence(40)) == []
    assert ingestion.audio_buffer.flush() == []


def test_own_strategy_ignores_the_provider_transcript_and_windows_the_mixed_audio():
    ingestion, received = service(TranscriptionStrategy.OWN, audio_buffer=AudioWindowBuffer(window_seconds=10))
    ingestion.add_transcript(event("Ignored.", 1))
    assert ingestion.add_audio(silence(5, speaker="1")) == []  # one person's own stream is skipped
    windows = ingestion.add_audio(silence(25))
    _, leftover = ingestion.finish()

    assert received == []
    assert [round(w.seconds) for w in windows] == [10, 10]
    assert [round(w.seconds) for w in leftover] == [5]


def test_compare_strategy_keeps_both():
    ingestion, received = service(TranscriptionStrategy.COMPARE, audio_buffer=AudioWindowBuffer(window_seconds=10))
    ingestion.add_transcript(event("Kept.", 1))
    windows = ingestion.add_audio(silence(10))
    ingestion.finish()

    assert [s.text for s in received] == ["Kept."]
    assert len(windows) == 1
