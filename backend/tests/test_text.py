import pytest

TEXT = "Gradient descent lowers the loss in small steps. The learning rate sets the size of each step."


def test_pasted_text_is_turned_into_notes(client):
    response = client.post("/api/text/process", json={"text": f"  {TEXT}  ", "title": "Week 6"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"]["type"] == "text"
    assert data["source"]["characters"] == len(TEXT)
    assert data["source"]["filename"] is None
    assert data["transcription"] is None
    assert data["text"] == TEXT
    assert data["lecture_notes"]["title"] == "Week 6"


@pytest.mark.parametrize("text", ["Too short.", "x" * 100_001])
def test_text_that_is_too_short_or_too_long_is_rejected(client, text):
    response = client.post("/api/text/process", json={"text": text})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
