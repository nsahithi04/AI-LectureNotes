import json
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors as genai_errors

from app.core import config
from app.engine.errors import EngineError
from app.engine import notes_generator

VALID_NOTES = {
    "title": "Machine Learning",
    "overview": "An introduction.",
    "learning_objectives": ["Define overfitting"],
    "sections": [
        {
            "heading": "Overfitting",
            "content": "A model memorises its training data.",
            "key_points": ["Split the data"],
            "definitions": [{"term": "Overfitting", "meaning": "Poor results on new data"}],
            "examples": [],
        }
    ],
    "important_concepts": ["Test set"],
    "key_takeaways": ["Always test on new data"],
    "conclusion": "Models must generalise.",
}


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls.append(contents)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(text=reply)


@pytest.fixture(autouse=True)
def gemini_settings(monkeypatch, fake_notes):
    monkeypatch.setattr(notes_generator, "generate_notes", fake_notes)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(notes_generator, "RETRY_DELAY_SECONDS", 0)


def use_replies(monkeypatch, *replies):
    client = FakeClient(replies)
    monkeypatch.setattr(notes_generator.genai, "Client", lambda **kwargs: client)
    return client


def api_error(code):
    error_class = genai_errors.ClientError if code < 500 else genai_errors.ServerError
    return error_class(code, {"error": {"message": "secret detail", "status": "ERROR"}})


def test_valid_notes_are_returned(monkeypatch):
    use_replies(monkeypatch, json.dumps(VALID_NOTES))

    notes = notes_generator.generate_notes("A lecture about overfitting.")

    assert notes.title == "Machine Learning"
    assert notes.sections[0].definitions[0].term == "Overfitting"


def test_transcript_and_title_are_sent(monkeypatch):
    client = use_replies(monkeypatch, json.dumps(VALID_NOTES))

    notes_generator.generate_notes("A lecture.", "Week 3")

    assert "Week 3" in client.calls[0]
    assert "<transcript>\nA lecture.\n</transcript>" in client.calls[0]


def test_malformed_json_is_retried(monkeypatch):
    client = use_replies(monkeypatch, "{not json", json.dumps(VALID_NOTES))

    assert notes_generator.generate_notes("A lecture.").title == "Machine Learning"
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    "bad_reply",
    [
        "{not json",
        "",
        json.dumps({"title": "Only a title"}),
        json.dumps({**VALID_NOTES, "sections": []}),
        json.dumps({**VALID_NOTES, "overview": "   "}),
    ],
)
def test_invalid_notes_are_never_returned(monkeypatch, bad_reply):
    client = use_replies(monkeypatch, bad_reply, bad_reply, bad_reply)

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "invalid_notes"
    assert len(client.calls) == notes_generator.MAX_ATTEMPTS


def test_rate_limit_is_reported_without_retrying(monkeypatch):
    client = use_replies(monkeypatch, api_error(429))

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "gemini_rate_limited"
    assert len(client.calls) == 1


def test_bad_key_is_reported_without_details(monkeypatch):
    use_replies(monkeypatch, api_error(403))

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "gemini_unavailable"
    assert "secret" not in error.value.message


def test_server_errors_are_retried(monkeypatch):
    client = use_replies(monkeypatch, api_error(503), json.dumps(VALID_NOTES))

    assert notes_generator.generate_notes("A lecture.").title == "Machine Learning"
    assert len(client.calls) == 2


def test_repeated_server_errors_are_reported(monkeypatch):
    use_replies(monkeypatch, api_error(500), api_error(503), api_error(500))

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "gemini_unavailable"


def test_network_errors_are_reported(monkeypatch):
    timeout = httpx.ReadTimeout("timed out")
    use_replies(monkeypatch, timeout, timeout, timeout)

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "gemini_unavailable"


def test_empty_transcript_is_rejected(monkeypatch):
    client = use_replies(monkeypatch)

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("   ")

    assert error.value.code == "empty_transcript"
    assert client.calls == []


def test_overly_long_transcript_is_rejected(monkeypatch):
    client = use_replies(monkeypatch)

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("x" * (notes_generator.MAX_TRANSCRIPT_CHARACTERS + 1))

    assert error.value.code == "transcript_too_long"
    assert client.calls == []


def test_missing_api_key_is_reported(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")

    with pytest.raises(EngineError) as error:
        notes_generator.generate_notes("A lecture.")

    assert error.value.code == "gemini_not_configured"
