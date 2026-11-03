import json

import pytest

from app.core import config
from app.engine import gemini_client, question_generator
from app.engine.errors import EngineError
from tests.test_notes import FakeClient


def mcq(number=1):
    options = [f"Option {number}{letter}" for letter in "ABCD"]
    return {"type": "multiple_choice", "topic": "Topic", "question": f"Question {number}?", "options": options, "answer": options[0]}


def short(number=1):
    return {"type": "short_answer", "topic": "Topic", "question": f"Explain {number}.", "options": [], "answer": "An answer."}


def reply(*questions):
    return json.dumps({"questions": list(questions)})


@pytest.fixture(autouse=True)
def gemini_settings(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_client, "RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", [])


def use_replies(monkeypatch, *replies):
    client = FakeClient(replies)
    monkeypatch.setattr(gemini_client.genai, "Client", lambda **kwargs: client)
    return client


def test_questions_are_generated(monkeypatch):
    use_replies(monkeypatch, reply(mcq(1), mcq(2)))

    questions = question_generator.generate_questions("A lecture.", 2, "multiple_choice")

    assert [question.question for question in questions] == ["Question 1?", "Question 2?"]


def test_the_answer_is_still_an_option_after_shuffling(monkeypatch):
    use_replies(monkeypatch, reply(mcq()))

    question = question_generator.generate_questions("A lecture.", 1, "multiple_choice")[0]

    assert sorted(question.options) == sorted(mcq()["options"])
    assert question.answer in question.options


def test_extra_questions_are_dropped(monkeypatch):
    use_replies(monkeypatch, reply(mcq(1), mcq(2), mcq(3)))

    assert len(question_generator.generate_questions("A lecture.", 2, "multiple_choice")) == 2


def test_the_count_type_and_teacher_request_reach_gemini(monkeypatch):
    client = use_replies(monkeypatch, reply(mcq(1), mcq(2), short(1)))

    question_generator.generate_questions("A lecture.", 3, "both", "Focus on overfitting")

    prompt = client.calls[0]
    assert "2 multiple choice and 1 short answer" in prompt
    assert "<teacher_request>\nFocus on overfitting\n</teacher_request>" in prompt
    assert "<transcript>\nA lecture.\n</transcript>" in prompt


def test_no_request_section_without_a_teacher_request(monkeypatch):
    client = use_replies(monkeypatch, reply(mcq()))

    question_generator.generate_questions("A lecture.", 1, "multiple_choice", "   ")

    assert "teacher_request" not in client.calls[0]


@pytest.mark.parametrize(
    "bad_question",
    [
        {**mcq(), "answer": "Not one of the options"},
        {**mcq(), "options": ["A", "B", "C"], "answer": "A"},
        {**mcq(), "options": ["A", "A", "B", "C"], "answer": "A"},
        {**mcq(), "question": "   "},
        {**short(), "options": ["An option"]},
        {**short(), "answer": ""},
    ],
)
def test_invalid_questions_are_retried_then_reported(monkeypatch, bad_question):
    client = use_replies(monkeypatch, *[reply(bad_question)] * gemini_client.MAX_ATTEMPTS)

    with pytest.raises(EngineError) as error:
        question_generator.generate_questions("A lecture.", 1, "both")

    assert error.value.code == "invalid_questions"
    assert len(client.calls) == gemini_client.MAX_ATTEMPTS


def test_too_few_questions_are_retried(monkeypatch):
    client = use_replies(monkeypatch, reply(mcq(1)), reply(mcq(1), mcq(2)))

    assert len(question_generator.generate_questions("A lecture.", 2, "multiple_choice")) == 2
    assert len(client.calls) == 2


def test_repeated_questions_only_count_once(monkeypatch):
    client = use_replies(monkeypatch, reply(mcq(1), mcq(1)), reply(mcq(1), mcq(2)))

    question_generator.generate_questions("A lecture.", 2, "multiple_choice")

    assert len(client.calls) == 2


def test_the_wrong_question_type_is_rejected(monkeypatch):
    client = use_replies(monkeypatch, reply(short()), reply(mcq()))

    assert question_generator.generate_questions("A lecture.", 1, "multiple_choice")[0].type == "multiple_choice"
    assert len(client.calls) == 2


def test_both_needs_both_types(monkeypatch):
    client = use_replies(monkeypatch, reply(mcq(1), mcq(2)), reply(mcq(1), short(1)))

    question_generator.generate_questions("A lecture.", 2, "both")

    assert len(client.calls) == 2


def test_the_endpoint_returns_questions(client, monkeypatch):
    use_replies(monkeypatch, reply(mcq()))

    response = client.post(
        "/api/questions/generate",
        json={"transcript": "A lecture.", "count": 1, "question_type": "multiple_choice"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["questions"][0]["question"] == "Question 1?"


@pytest.mark.parametrize(
    "change",
    [{"count": 0}, {"count": 51}, {"question_type": "essay"}, {"instructions": "x" * 1001}],
)
def test_the_endpoint_rejects_bad_requests(client, change):
    body = {"transcript": "A lecture.", "count": 1, "question_type": "both", **change}

    response = client.post("/api/questions/generate", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_the_endpoint_reports_invalid_questions(client, monkeypatch):
    use_replies(monkeypatch, *["{not json"] * gemini_client.MAX_ATTEMPTS)

    response = client.post(
        "/api/questions/generate",
        json={"transcript": "A lecture.", "count": 1, "question_type": "both"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_questions"
