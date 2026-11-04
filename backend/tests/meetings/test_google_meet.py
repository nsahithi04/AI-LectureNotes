from urllib.parse import parse_qs, urlparse

import pytest

from app.core import config
from app.services import meetings_service

REDIRECT = "http://127.0.0.1:8000/api/meetings/google_meet/callback"
TEACHER = "local-teacher"


def connect(client, fake_google):
    """Go through the whole sign-in, the way a browser would. Returns where the teacher ends up."""
    sign_in = client.get("/api/meetings/google_meet/connect", follow_redirects=False)
    query = parse_qs(urlparse(sign_in.headers["location"]).query)
    code = fake_google.issue_code(query["code_challenge"][0])
    callback = client.get(
        "/api/meetings/google_meet/callback", params={"code": code, "state": query["state"][0]}, follow_redirects=False
    )
    return callback.headers["location"]


def add_meeting(fake_google, record_id="rec1", start="2026-11-03T09:00:00Z", end="2026-11-03T10:00:00Z", transcript="ENDED"):
    fake_google.records[record_id] = {
        "name": f"conferenceRecords/{record_id}",
        "startTime": start,
        "endTime": end,
        "space": f"spaces/{record_id}-space",
    }
    fake_google.spaces[f"spaces/{record_id}-space"] = {"name": f"spaces/{record_id}-space", "meetingCode": "abc-mnop-xyz"}
    if transcript:
        fake_google.transcripts[record_id] = [{"name": f"conferenceRecords/{record_id}/transcripts/t1", "state": transcript}]
    fake_google.participants[record_id] = [
        {"name": f"conferenceRecords/{record_id}/participants/p1", "signedinUser": {"user": "users/1", "displayName": "Dr Rao"}},
        {"name": f"conferenceRecords/{record_id}/participants/p2", "anonymousUser": {"displayName": "Asha"}},
        {"name": f"conferenceRecords/{record_id}/participants/p3"},
    ]


def entry(record_id, n, participant, start, end, text):
    return {
        "name": f"conferenceRecords/{record_id}/transcripts/t1/entries/e{n}",
        "participant": f"conferenceRecords/{record_id}/participants/{participant}",
        "text": text,
        "languageCode": "en-US",
        "startTime": start,
        "endTime": end,
    }


# Connecting -------------------------------------------------------------------------------------------


def test_connect_sends_the_teacher_to_google_with_offline_access_and_pkce(client):
    response = client.get("/api/meetings/google_meet/connect", follow_redirects=False)

    assert response.status_code == 302
    url = urlparse(response.headers["location"])
    query = {key: values[0] for key, values in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://accounts.google.com/o/oauth2/v2/auth"
    assert query["client_id"] == config.GOOGLE_OAUTH_CLIENT_ID
    assert query["redirect_uri"] == REDIRECT
    assert query["scope"].split() == ["openid", "email", "https://www.googleapis.com/auth/meetings.space.readonly"]
    assert query["access_type"] == "offline"
    assert query["code_challenge_method"] == "S256"
    assert len(query["state"]) > 30
    assert "test-secret" not in response.headers["location"]


def test_signing_in_saves_the_connection_and_returns_to_the_frontend(client, fake_google, meeting_storage):
    _, tokens = meeting_storage

    assert connect(client, fake_google) == "http://localhost:5173/integrations?provider=google_meet&connected=1"
    saved = tokens.get("google_meet", TEACHER)
    assert saved["refresh_token"] == "refresh-1"
    assert saved["account"] == "teacher@school.edu"

    response = client.get("/api/meetings/connections")
    assert {"provider": "google_meet", "connected": True, "account": "teacher@school.edu"} in response.json()["data"]
    assert "access-1" not in response.text and "refresh-1" not in response.text


def test_a_callback_with_an_unknown_or_reused_state_is_refused(client, fake_google, meeting_storage):
    _, tokens = meeting_storage
    sign_in = client.get("/api/meetings/google_meet/connect", follow_redirects=False)
    query = parse_qs(urlparse(sign_in.headers["location"]).query)
    code = fake_google.issue_code(query["code_challenge"][0])

    forged = client.get("/api/meetings/google_meet/callback", params={"code": code, "state": "made-up"}, follow_redirects=False)
    assert forged.headers["location"].endswith("error=invalid_connection")

    first = client.get("/api/meetings/google_meet/callback", params={"code": code, "state": query["state"][0]}, follow_redirects=False)
    again = client.get("/api/meetings/google_meet/callback", params={"code": code, "state": query["state"][0]}, follow_redirects=False)
    assert first.headers["location"].endswith("connected=1")
    assert again.headers["location"].endswith("error=invalid_connection")
    assert tokens.get("google_meet", TEACHER) is not None


def test_cancelling_on_googles_page_is_reported(client, meeting_storage):
    _, tokens = meeting_storage
    sign_in = client.get("/api/meetings/google_meet/connect", follow_redirects=False)
    state = parse_qs(urlparse(sign_in.headers["location"]).query)["state"][0]

    response = client.get("/api/meetings/google_meet/callback", params={"error": "access_denied", "state": state}, follow_redirects=False)

    assert response.headers["location"] == "http://localhost:5173/integrations?provider=google_meet&error=access_denied"
    assert tokens.get("google_meet", TEACHER) is None


def test_unticking_the_meet_permission_is_reported(client, fake_google, meeting_storage):
    _, tokens = meeting_storage
    fake_google.granted_scope = "openid email"

    assert connect(client, fake_google).endswith("error=missing_permission")
    assert tokens.get("google_meet", TEACHER) is None


def test_disconnecting_revokes_access_and_forgets_the_tokens(client, fake_google, meeting_storage):
    _, tokens = meeting_storage
    connect(client, fake_google)

    response = client.post("/api/meetings/google_meet/disconnect")

    assert response.json()["data"] == {"provider": "google_meet", "connected": False, "account": None}
    assert fake_google.revoked == ["refresh-1"]
    assert tokens.get("google_meet", TEACHER) is None


def test_without_google_credentials_the_provider_reports_it_isnt_set_up(client, monkeypatch, fake_google):
    monkeypatch.setattr(config, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    tokens, states = meetings_service.tokens, meetings_service.states
    monkeypatch.setattr(meetings_service, "registry", meetings_service.create_registry(tokens, states, fake_google.transport()))

    providers = {p["id"]: p for p in client.get("/api/meetings/providers").json()["data"]}
    response = client.get("/api/meetings/google_meet/connect", follow_redirects=False)

    assert providers["google_meet"]["availability"] == "not_configured"
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_not_configured"


# Meetings ---------------------------------------------------------------------------------------------


def test_meetings_are_listed_newest_first_with_their_transcript_status(client, fake_google):
    connect(client, fake_google)
    add_meeting(fake_google, "old", start="2026-11-01T09:00:00Z", end="2026-11-01T10:00:00Z")
    add_meeting(fake_google, "untranscribed", start="2026-11-02T09:00:00Z", end="2026-11-02T10:00:00Z", transcript=None)
    add_meeting(fake_google, "running", start="2026-11-03T09:00:00Z", end=None, transcript="STARTED")

    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 200
    meetings = response.json()["data"]
    assert [(m["provider_meeting_id"], m["transcript_status"]) for m in meetings] == [
        ("running", "processing"),
        ("untranscribed", "none"),
        ("old", "available"),
    ]
    assert meetings[2]["title"] == "Google Meet (abc-mnop-xyz)"
    assert meetings[2]["started_at"] == "2026-11-01T09:00:00Z"


def test_importing_a_meeting_keeps_speaker_names_and_times(client, fake_google, meeting_storage):
    sessions, _ = meeting_storage
    connect(client, fake_google)
    add_meeting(fake_google)
    fake_google.entries["conferenceRecords/rec1/transcripts/t1"] = [
        entry("rec1", 1, "p1", "2026-11-03T09:00:05.123456789Z", "2026-11-03T09:00:08Z", "Today we cover overfitting."),
        entry("rec1", 2, "p2", "2026-11-03T09:00:10Z", "2026-11-03T09:00:12Z", "Is that the same as"),
        entry("rec1", 3, "p2", "2026-11-03T09:00:12.500Z", "2026-11-03T09:00:14Z", "memorising the data?"),
        entry("rec1", 4, "p3", "2026-11-03T09:01:00Z", "2026-11-03T09:01:02Z", "Hello?"),
    ]

    response = client.post("/api/meetings/google_meet/meetings/rec1/import")

    assert response.status_code == 200
    session = response.json()["data"]
    assert session["status"] == "completed"
    assert session["processing_mode"] == "post_meeting"
    assert session["title"] == "Google Meet (abc-mnop-xyz)"
    assert [p["name"] for p in session["participants"]] == ["Dr Rao", "Asha", None]
    transcript = client.get(f"/api/meetings/sessions/{session['id']}/transcript").json()["data"]
    assert [(s["speaker_name"], s["start_time"], s["text"]) for s in transcript] == [
        ("Dr Rao", 5.123, "Today we cover overfitting."),
        ("Asha", 10.0, "Is that the same as memorising the data?"),  # one sentence, split by Google
        ("Speaker 1", 60.0, "Hello?"),  # someone Google has no name for
    ]
    assert transcript[0]["source"] == "google_meet"
    assert transcript[0]["language"] == "en-US"

    # Importing again gives the same session instead of a copy.
    again = client.post("/api/meetings/google_meet/meetings/rec1/import").json()["data"]
    assert again["id"] == session["id"]
    assert len(sessions.all()) == 1


def test_long_transcripts_are_read_page_by_page(client, fake_google):
    connect(client, fake_google)
    add_meeting(fake_google)
    fake_google.entries["conferenceRecords/rec1/transcripts/t1"] = [
        entry("rec1", n, "p1", f"2026-11-03T09:{n // 60:02d}:{n % 60:02d}Z", None, f"Sentence {n}.") for n in range(150)
    ]

    session = client.post("/api/meetings/google_meet/meetings/rec1/import").json()["data"]

    transcript = client.get(f"/api/meetings/sessions/{session['id']}/transcript").json()["data"]
    assert len(transcript) == 150
    assert transcript[-1]["text"] == "Sentence 149."
    assert fake_google.entries_page_size_seen == [100, 100]


@pytest.mark.parametrize(
    "transcript, status, code",
    [("STARTED", 409, "transcript_not_ready"), (None, 422, "no_transcript")],
)
def test_meetings_without_a_finished_transcript_are_explained(client, fake_google, transcript, status, code):
    connect(client, fake_google)
    add_meeting(fake_google, transcript=transcript)

    response = client.post("/api/meetings/google_meet/meetings/rec1/import")

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_odd_meeting_ids_never_reach_google(client, fake_google):
    connect(client, fake_google)
    before = len(fake_google.requests)

    response = client.post("/api/meetings/google_meet/meetings/rec1%3Fx=1/import")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert len(fake_google.requests) == before


def test_an_expired_access_token_is_refreshed_and_saved(client, fake_google, meeting_storage):
    _, tokens = meeting_storage
    connect(client, fake_google)
    saved = tokens.get("google_meet", TEACHER)
    tokens.save("google_meet", TEACHER, {**saved, "expires_at": 0})

    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 200
    assert fake_google.refresh_count == 1
    assert tokens.get("google_meet", TEACHER)["access_token"] == "access-2"
    assert tokens.get("google_meet", TEACHER)["refresh_token"] == "refresh-1"


def test_a_token_google_rejects_early_is_refreshed_once(client, fake_google):
    connect(client, fake_google)
    fake_google.access_token = "access-reissued"  # Google no longer accepts the saved token

    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 200
    assert fake_google.refresh_count == 1


def test_a_revoked_connection_asks_the_teacher_to_connect_again(client, fake_google, meeting_storage):
    _, tokens = meeting_storage
    connect(client, fake_google)
    fake_google.access_token = "access-reissued"
    fake_google.refresh_fails = True

    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "reconnect_required"
    assert tokens.get("google_meet", TEACHER) is None


def test_listing_meetings_before_connecting_is_explained(client):
    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_connected"


def test_googles_permission_errors_are_passed_on_clearly(client, fake_google):
    connect(client, fake_google)
    fake_google.errors["conferenceRecords"] = (403, "Google Meet API has not been used in project 123.")

    response = client.get("/api/meetings/google_meet/meetings")

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "permission_denied"
    assert "Google Meet API is turned on" in error["message"]
    assert "has not been used in project 123" in error["message"]


# Notes ------------------------------------------------------------------------------------------------


def test_notes_are_made_from_the_imported_transcript_with_speakers(client, fake_google):
    connect(client, fake_google)
    add_meeting(fake_google)
    fake_google.entries["conferenceRecords/rec1/transcripts/t1"] = [
        entry("rec1", 1, "p1", "2026-11-03T09:00:05Z", "2026-11-03T09:00:08Z", "Today we cover overfitting."),
        entry("rec1", 2, "p2", "2026-11-03T10:02:03Z", "2026-11-03T10:02:05Z", "Thank you."),
    ]
    session = client.post("/api/meetings/google_meet/meetings/rec1/import").json()["data"]

    response = client.post(f"/api/meetings/sessions/{session['id']}/notes", json={"title": "Week 5"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["text"] == "[0:05] Dr Rao: Today we cover overfitting.\n[1:02:03] Asha: Thank you."
    assert data["lecture_notes"]["title"] == "Week 5"
    # The fake notes generator copies its input into the first section.
    assert data["lecture_notes"]["sections"][0]["content"] == data["text"]

    untitled = client.post(f"/api/meetings/sessions/{session['id']}/notes")
    assert untitled.json()["data"]["lecture_notes"]["title"] == "Google Meet (abc-mnop-xyz)"


def test_notes_for_a_missing_session_are_404(client):
    response = client.post("/api/meetings/sessions/missing/notes")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"
