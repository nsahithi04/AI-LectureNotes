import pytest

from app.core import config
from app.meetings.oauth import OAuthStateStore
from app.meetings.session_store import JsonFileSessionStore
from app.meetings.token_store import DevFileTokenStore
from app.services import meetings_service
from tests.meetings.fake_google import FakeGoogle

MEETING_START = 1_727_384_000_000  # milliseconds since the epoch, like Zoom's timestamps


@pytest.fixture
def fake_google():
    return FakeGoogle()


@pytest.fixture(autouse=True)
def meeting_storage(tmp_path, monkeypatch, fake_google):
    """Every test gets empty, temporary meeting storage, and a Google Meet that talks to a fake Google."""
    sessions = JsonFileSessionStore(tmp_path / "sessions")
    tokens = DevFileTokenStore(tmp_path / "tokens.json")
    states = OAuthStateStore()
    monkeypatch.setattr(config, "GOOGLE_OAUTH_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setattr(config, "GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(config, "FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setattr(meetings_service, "sessions", sessions)
    monkeypatch.setattr(meetings_service, "tokens", tokens)
    monkeypatch.setattr(meetings_service, "states", states)
    monkeypatch.setattr(meetings_service, "registry", meetings_service.create_registry(tokens, states, fake_google.transport()))
    return sessions, tokens
