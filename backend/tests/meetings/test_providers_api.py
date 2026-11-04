import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.meetings.errors import MeetingError
from app.meetings.providers.base import PlannedProvider
from app.meetings.providers.registry import GOOGLE_MEET, MICROSOFT_TEAMS, ZOOM, ProviderRegistry, build_registry
from app.meetings.schemas import Capability, MeetingSession, ProcessingMode, ProviderId, TranscriptSegment

MEETINGS_DIR = Path(__file__).parents[2] / "app" / "meetings"
ENGINE_DIR = Path(__file__).parents[2] / "app" / "engine"


def test_every_provider_lists_honest_capabilities():
    providers = {info.id: info for info in build_registry().list_info()}

    assert set(providers) == {ProviderId.ZOOM, ProviderId.GOOGLE_MEET, ProviderId.MICROSOFT_TEAMS}
    assert Capability.LIVE_TRANSCRIPT in providers[ProviderId.ZOOM].capabilities
    for post_meeting_only in (ProviderId.GOOGLE_MEET, ProviderId.MICROSOFT_TEAMS):
        assert providers[post_meeting_only].processing_modes == [ProcessingMode.POST_MEETING]
        assert Capability.LIVE_TRANSCRIPT not in providers[post_meeting_only].capabilities
        assert Capability.LIVE_AUDIO not in providers[post_meeting_only].capabilities


@pytest.mark.anyio
async def test_a_planned_provider_supports_nothing_yet():
    provider = PlannedProvider(ZOOM)

    assert not provider.supports(Capability.LIVE_TRANSCRIPT)
    with pytest.raises(MeetingError) as error:
        await provider.connect("teacher-1")
    assert error.value.code == "provider_not_available"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_unknown_providers_are_reported():
    with pytest.raises(MeetingError) as error:
        ProviderRegistry([PlannedProvider(GOOGLE_MEET), PlannedProvider(MICROSOFT_TEAMS)]).get("skype")

    assert error.value.code == "provider_not_found"


def test_providers_endpoint(client):
    response = client.get("/api/meetings/providers")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [(p["id"], p["availability"]) for p in data] == [
        ("zoom", "planned"),
        ("google_meet", "available"),  # the tests give it credentials
        ("microsoft_teams", "planned"),
    ]


def test_connections_endpoint(client, meeting_storage):
    _, tokens = meeting_storage
    tokens.save("zoom", "local-teacher", {"access_token": "secret"})
    response = client.get("/api/meetings/connections")

    assert response.json()["data"] == [
        {"provider": "zoom", "connected": True, "account": None},
        {"provider": "google_meet", "connected": False, "account": None},
        {"provider": "microsoft_teams", "connected": False, "account": None},
    ]
    assert "secret" not in response.text


def test_session_and_transcript_endpoints(client, meeting_storage):
    sessions, _ = meeting_storage
    sessions.save(
        MeetingSession(
            id="s1",
            provider=ProviderId.ZOOM,
            provider_meeting_id="123",
            started_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
            processing_mode=ProcessingMode.LIVE,
        )
    )
    sessions.add_segments(
        "s1",
        [
            TranscriptSegment(id="b", speaker_name="Asha", start_time=4, end_time=5, text="Second.", source="zoom_rtms"),
            TranscriptSegment(id="a", speaker_name="Teacher", start_time=1, end_time=2, text="First.", source="zoom_rtms"),
        ],
    )

    assert [s["id"] for s in client.get("/api/meetings/sessions").json()["data"]] == ["s1"]
    assert client.get("/api/meetings/sessions/s1").json()["data"]["status"] == "waiting"
    transcript = client.get("/api/meetings/sessions/s1/transcript").json()["data"]
    assert [(s["speaker_name"], s["text"]) for s in transcript] == [("Teacher", "First."), ("Asha", "Second.")]


@pytest.mark.parametrize("path", ["/api/meetings/sessions/missing", "/api/meetings/sessions/missing/transcript"])
def test_missing_sessions_are_404(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


def imports(folder):
    for path in folder.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                yield path, [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                yield path, [node.module]


def test_the_meetings_layer_has_no_web_code():
    forbidden = ("fastapi", "starlette", "app.api", "app.services")
    assert not [(p.name, m) for p, modules in imports(MEETINGS_DIR) for m in modules if m.startswith(forbidden)]


def test_the_engine_knows_nothing_about_meeting_providers():
    assert not [(p.name, m) for p, modules in imports(ENGINE_DIR) for m in modules if m.startswith("app.meetings")]
