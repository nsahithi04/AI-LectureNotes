from app.meetings.events import TranscriptEvent
from app.meetings.normalizer import TranscriptNormalizer, ends_sentence
from tests.meetings.conftest import MEETING_START


def event(text, start_s, end_s=None, speaker="1", name="Teacher", language="en", source="zoom_rtms"):
    end_ms = None if end_s is None else MEETING_START + int(end_s * 1000)
    return TranscriptEvent(speaker, name, MEETING_START + int(start_s * 1000), end_ms, text, language, source)


def normalizer():
    return TranscriptNormalizer("s1", meeting_start_ms=MEETING_START)


def test_times_are_seconds_from_the_meeting_start_and_raw_times_are_kept():
    n = normalizer()
    n.add(event("Today we will discuss supervised learning.", 12.5, 18.2))
    [segment] = n.flush()

    assert segment.model_dump() == {
        "id": "s1-00001",
        "speaker_id": "1",
        "speaker_name": "Teacher",
        "start_time": 12.5,
        "end_time": 18.2,
        "text": "Today we will discuss supervised learning.",
        "language": "en",
        "source": "zoom_rtms",
        "source_timestamp_ms": MEETING_START + 12_500,
    }


def test_a_new_speaker_completes_the_previous_segment():
    n = normalizer()
    assert n.add(event("Any questions?", 1, 2)) == []
    [teacher] = n.add(event("Yes, what is a label?", 3, 4, speaker="2", name="Asha"))

    assert (teacher.speaker_name, teacher.text) == ("Teacher", "Any questions?")
    assert n.flush()[0].speaker_name == "Asha"


def test_fragments_of_one_sentence_are_joined():
    n = normalizer()
    n.add(event("Overfitting happens when", 1, 2))
    n.add(event("a model memorises", 2.5, 3.5))
    n.add(event("its training data.", 4, 5))
    [joined] = n.add(event("Next topic.", 5.5, 6))

    assert joined.text == "Overfitting happens when a model memorises its training data."
    assert (joined.start_time, joined.end_time) == (1.0, 5.0)


def test_finished_sentences_and_long_pauses_are_not_joined():
    n = normalizer()
    completed = []
    for text, start, end in [("This is a full sentence.", 1, 2), ("So is this.", 2.2, 3), ("An unfinished thought", 3.5, 4), ("after a long pause", 10, 11)]:
        completed += n.add(event(text, start, end))

    assert [s.text for s in completed] == ["This is a full sentence.", "So is this.", "An unfinished thought"]


def test_an_unfinished_sentence_is_kept_when_the_speaker_goes_quiet():
    n = normalizer()
    n.add(event("and then the model", 1, 2))

    assert n.flush_if_idle(MEETING_START + 3000, idle_ms=4000) == []
    [segment] = n.flush_if_idle(MEETING_START + 6000, idle_ms=4000)
    assert segment.text == "and then the model"


def test_repeated_text_is_dropped_even_with_new_ids():
    n = normalizer()
    n.add(event("Welcome, everyone!", 1, 2))
    n.add(event("welcome everyone", 1.2, 2.1))  # the same words, sent again

    assert [s.text for s in n.flush()] == ["Welcome, everyone!"]


def test_unnamed_speakers_get_stable_labels_and_known_names_are_used():
    n = normalizer()
    n.set_participant("7", "Ravi")
    names = []
    for text, start, speaker in [("Hello.", 1, "9"), ("Hi.", 3, "7"), ("Again.", 5, "9"), ("Bye.", 7, "8")]:
        names += [s.speaker_name for s in n.add(event(text, start, start + 1, speaker=speaker, name=None))]
    names += [s.speaker_name for s in n.flush()]

    assert names == ["Speaker 1", "Ravi", "Speaker 1", "Speaker 2"]


def test_times_never_go_negative_or_end_before_they_start():
    n = normalizer()
    n.add(event("Before the start.", -5, -10))
    [segment] = n.flush()

    assert (segment.start_time, segment.end_time) == (0, 0)


def test_the_first_event_sets_the_start_when_the_meeting_start_is_unknown():
    n = TranscriptNormalizer("s1")
    n.add(event("First words.", 30, 31))
    [segment] = n.flush()

    assert segment.start_time == 0


def test_language_and_source_are_kept_and_sources_are_never_mixed():
    n = normalizer()
    n.add(event("Hola a todos", 1, 2, language="es"))
    [zoom] = n.add(event("Hola a todos y bienvenidos", 2.1, 3, language="es", source="whisper"))

    assert (zoom.language, zoom.source) == ("es", "zoom_rtms")
    assert n.flush()[0].source == "whisper"


def test_sentence_endings_are_recognised():
    assert ends_sentence("Done.") and ends_sentence("Really?\"") and ends_sentence("终于。")
    assert not ends_sentence("and then")
