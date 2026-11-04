"""Google Meet: transcripts after the meeting, through the Google Meet REST API (v2).

The teacher signs in with Google once. LectureAI asks for offline access, so it can fetch transcripts
later without asking again. It lists the teacher's recent meetings ("conference records") and imports
a transcript's entries with each speaker's name.

Outside LectureAI's control:
- A transcript only exists if someone turned on transcription during the meeting, and only on Workspace
  editions that include it (such as Education Plus, Teaching and Learning Upgrade or Business Standard).
- Google deletes transcript entries 30 days after the meeting.
- The Google Meet REST API must be turned on in the Google Cloud project that owns the OAuth client.
"""

import asyncio
import re
import time
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urlencode

import httpx

from app.meetings.errors import MeetingError
from app.meetings.events import TranscriptEvent
from app.meetings.normalizer import TranscriptNormalizer
from app.meetings.oauth import OAuthStateStore, id_token_email
from app.meetings.providers.base import MeetingProvider
from app.meetings.schemas import (
    Availability,
    MeetingDetails,
    MeetingSummary,
    Participant,
    ProviderInfo,
    TranscriptSegment,
    TranscriptStatus,
)
from app.meetings.token_store import TokenStore

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
MEET_API = "https://meet.googleapis.com/v2"

MEET_SCOPE = "https://www.googleapis.com/auth/meetings.space.readonly"
SCOPES = ["openid", "email", MEET_SCOPE]

SOURCE = "google_meet"
MAX_MEETINGS = 25
MAX_ENTRY_PAGES = 200  # 100 entries a page: far more than a long class needs
REFRESH_MARGIN_SECONDS = 60
# Meet IDs are letters, digits, "-" and "_". Checking stops anything else being put into Google's URLs.
MEETING_ID = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
# A transcript is ready to read once Google has finished it; it may also have made a Google Doc of it.
FINISHED_TRANSCRIPT_STATES = {"ENDED", "FILE_GENERATED"}


def parse_time(value: Optional[str]) -> Optional[datetime]:
    """An RFC 3339 time from Google. Python reads at most 6 decimal places, and Google may send 9."""
    if not value:
        return None
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", value).replace("Z", "+00:00"))


def to_ms(value: Optional[str]) -> Optional[int]:
    parsed = parse_time(value)
    return int(parsed.timestamp() * 1000) if parsed else None


def participant_name(participant: dict) -> Optional[str]:
    for kind in ("signedinUser", "anonymousUser", "phoneUser"):
        name = participant.get(kind, {}).get("displayName")
        if name:
            return name
    return None


def transcript_status(record: dict, transcripts: list[dict]) -> TranscriptStatus:
    if any(t.get("state") in FINISHED_TRANSCRIPT_STATES for t in transcripts):
        return TranscriptStatus.AVAILABLE
    if transcripts or not record.get("endTime"):
        return TranscriptStatus.PROCESSING
    return TranscriptStatus.NONE


class GoogleMeetProvider(MeetingProvider):
    def __init__(
        self,
        info: ProviderInfo,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tokens: TokenStore,
        states: OAuthStateStore,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        clock: Callable[[], float] = time.time,
    ):
        configured = bool(client_id and client_secret)
        self._info = info.model_copy(update={"availability": Availability.AVAILABLE if configured else Availability.NOT_CONFIGURED})
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.tokens = tokens
        self.states = states
        self.transport = transport
        self.clock = clock

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @property
    def _key(self) -> str:
        return self._info.id.value

    def _require_configured(self, action: str) -> None:
        if self._info.availability != Availability.AVAILABLE:
            raise self._unsupported(action)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport, timeout=20)

    # Connecting -------------------------------------------------------------------------------------

    async def connect(self, user_id: str) -> str:
        self._require_configured("connecting an account")
        state, challenge = self.states.create(self._key, user_id)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",  # a refresh token, to fetch transcripts after the meeting
            "prompt": "consent",       # Google only sends a refresh token when consent is shown
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def complete_connection(self, code: str, state: str) -> None:
        self._require_configured("connecting an account")
        pending = self.states.consume(self._key, state)
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": pending.code_verifier,
        }
        async with self._client() as client:
            response = await self._post(client, TOKEN_URL, data)
        if response.status_code != 200:
            raise MeetingError("invalid_connection", "Google didn't accept the sign-in. Please connect again.")
        body = response.json()
        # Google lets people untick permissions on the consent screen.
        if MEET_SCOPE not in body.get("scope", "").split():
            raise MeetingError(
                "missing_permission",
                "LectureAI needs permission to see your Google Meet meetings and transcripts. Connect again and allow it.",
            )
        self.tokens.save(
            self._key,
            pending.user_id,
            {
                "access_token": body["access_token"],
                "refresh_token": body.get("refresh_token"),
                "expires_at": self.clock() + int(body.get("expires_in", 3600)),
                "account": id_token_email(body.get("id_token")),
            },
        )

    async def disconnect(self, user_id: str) -> None:
        saved = self.tokens.get(self._key, user_id)
        if not saved:
            return
        token = saved.get("refresh_token") or saved.get("access_token")
        if token:
            try:
                # Revoking tells Google to stop LectureAI's access too. It's best effort: the saved
                # tokens are deleted either way, and the teacher can also remove access in their Google account.
                async with self._client() as client:
                    await client.post(REVOKE_URL, data={"token": token})
            except httpx.HTTPError:
                pass
        self.tokens.delete(self._key, user_id)

    # Meetings ---------------------------------------------------------------------------------------

    async def list_meetings(self, user_id: str) -> list[MeetingSummary]:
        self._require_configured("listing meetings")
        async with self._client() as client:
            data = await self._get(client, user_id, "conferenceRecords", {"pageSize": MAX_MEETINGS})
            records = data.get("conferenceRecords", [])[:MAX_MEETINGS]
            details = await asyncio.gather(*(self._summary(client, user_id, record) for record in records))
        return sorted(details, key=lambda m: m.started_at.timestamp() if m.started_at else 0, reverse=True)

    async def get_meeting_details(self, user_id: str, provider_meeting_id: str) -> MeetingDetails:
        self._require_configured("meeting details")
        record_name = self._record_name(provider_meeting_id)
        async with self._client() as client:
            record = await self._get(client, user_id, record_name)
            summary, participants = await asyncio.gather(
                self._summary(client, user_id, record), self._participants(client, user_id, record_name)
            )
        return MeetingDetails(
            **summary.model_dump(),
            participants=[
                Participant(
                    id=p["name"],
                    name=participant_name(p),
                    joined_at=parse_time(p.get("earliestStartTime")),
                    left_at=parse_time(p.get("latestEndTime")),
                )
                for p in participants
            ],
        )

    async def retrieve_transcript(self, user_id: str, provider_meeting_id: str, session_id: str) -> list[TranscriptSegment]:
        self._require_configured("transcripts after the meeting")
        record_name = self._record_name(provider_meeting_id)
        async with self._client() as client:
            record = await self._get(client, user_id, record_name)
            transcripts, participants = await asyncio.gather(
                self._pages(client, user_id, f"{record_name}/transcripts", "transcripts", 10),
                self._participants(client, user_id, record_name),
            )
            # Transcription can be turned off and on again, which makes several transcripts in one meeting.
            finished = sorted(
                (t for t in transcripts if t.get("state") in FINISHED_TRANSCRIPT_STATES),
                key=lambda t: t.get("startTime", ""),
            )
            entry_lists = [
                await self._pages(client, user_id, f"{t['name']}/entries", "transcriptEntries", MAX_ENTRY_PAGES, page_size=100)
                for t in finished
            ]

        normalizer = TranscriptNormalizer(session_id, meeting_start_ms=to_ms(record.get("startTime")))
        for participant in participants:
            normalizer.set_participant(participant["name"], participant_name(participant))
        segments: list[TranscriptSegment] = []
        for entries in entry_lists:
            for entry in entries:
                start_ms = to_ms(entry.get("startTime"))
                if start_ms is None or not entry.get("text"):
                    continue
                segments += normalizer.add(
                    TranscriptEvent(
                        speaker_id=entry.get("participant"),
                        speaker_name=None,
                        start_ms=start_ms,
                        end_ms=to_ms(entry.get("endTime")),
                        text=entry["text"],
                        language=entry.get("languageCode"),
                        source=SOURCE,
                        event_id=entry.get("name"),
                    )
                )
        return segments + normalizer.flush()

    def _record_name(self, provider_meeting_id: str) -> str:
        if not MEETING_ID.match(provider_meeting_id):
            raise MeetingError("meeting_not_found", "Meeting not found.")
        return f"conferenceRecords/{provider_meeting_id}"

    async def _summary(self, client: httpx.AsyncClient, user_id: str, record: dict) -> MeetingSummary:
        transcripts_data, space = await asyncio.gather(
            self._get(client, user_id, f"{record['name']}/transcripts"),
            self._space(client, user_id, record.get("space")),
        )
        code = (space or {}).get("meetingCode")
        return MeetingSummary(
            provider=self._info.id,
            provider_meeting_id=record["name"].split("/", 1)[1],
            title=f"Google Meet ({code})" if code else "Google Meet",
            started_at=parse_time(record.get("startTime")),
            ended_at=parse_time(record.get("endTime")),
            transcript_status=transcript_status(record, transcripts_data.get("transcripts", [])),
        )

    async def _space(self, client: httpx.AsyncClient, user_id: str, space_name: Optional[str]) -> Optional[dict]:
        """The meeting space, for its meeting code. Only a label, so a failure here doesn't stop anything."""
        if not space_name:
            return None
        try:
            return await self._get(client, user_id, space_name)
        except MeetingError as error:
            if error.code in ("not_connected", "reconnect_required"):
                raise
            return None

    async def _participants(self, client: httpx.AsyncClient, user_id: str, record_name: str) -> list[dict]:
        return await self._pages(client, user_id, f"{record_name}/participants", "participants", 20, page_size=250)

    # Talking to Google ------------------------------------------------------------------------------

    async def _pages(
        self, client: httpx.AsyncClient, user_id: str, path: str, key: str, max_pages: int, page_size: int = 100
    ) -> list[dict]:
        items: list[dict] = []
        page_token = None
        for _ in range(max_pages):
            params = {"pageSize": page_size, **({"pageToken": page_token} if page_token else {})}
            data = await self._get(client, user_id, path, params)
            items += data.get(key, [])
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return items

    async def _post(self, client: httpx.AsyncClient, url: str, data: dict) -> httpx.Response:
        try:
            return await client.post(url, data=data)
        except httpx.HTTPError:
            raise MeetingError("provider_error", "LectureAI couldn't reach Google. Try again in a moment.") from None

    async def _get(self, client: httpx.AsyncClient, user_id: str, path: str, params: Optional[dict] = None) -> dict:
        saved = await self._fresh_tokens(client, user_id)
        response = await self._send(client, path, saved, params)
        if response.status_code == 401:
            # The access token stopped working early (for example, it was revoked and reissued).
            saved = await self._refresh(client, user_id, saved)
            response = await self._send(client, path, saved, params)
        self._raise_for_error(response)
        return response.json()

    async def _send(self, client: httpx.AsyncClient, path: str, saved: dict, params: Optional[dict]) -> httpx.Response:
        try:
            return await client.get(
                f"{MEET_API}/{path}", params=params, headers={"Authorization": f"Bearer {saved['access_token']}"}
            )
        except httpx.HTTPError:
            raise MeetingError("provider_error", "LectureAI couldn't reach Google. Try again in a moment.") from None

    async def _fresh_tokens(self, client: httpx.AsyncClient, user_id: str) -> dict:
        saved = self.tokens.get(self._key, user_id)
        if not saved:
            raise MeetingError("not_connected", "Connect your Google account first.")
        if saved.get("expires_at", 0) - REFRESH_MARGIN_SECONDS <= self.clock():
            saved = await self._refresh(client, user_id, saved)
        return saved

    async def _refresh(self, client: httpx.AsyncClient, user_id: str, saved: dict) -> dict:
        if not saved.get("refresh_token"):
            self.tokens.delete(self._key, user_id)
            raise MeetingError("reconnect_required", "Your Google connection has expired. Please connect again.")
        response = await self._post(
            client,
            TOKEN_URL,
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": saved["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        if response.status_code in (400, 401):
            # The teacher removed LectureAI's access, changed their password, or the token expired.
            self.tokens.delete(self._key, user_id)
            raise MeetingError("reconnect_required", "Your Google connection has expired. Please connect again.")
        if response.status_code != 200:
            raise MeetingError("provider_error", "Google couldn't refresh the connection. Try again in a moment.")
        body = response.json()
        saved = {
            **saved,
            "access_token": body["access_token"],
            "expires_at": self.clock() + int(body.get("expires_in", 3600)),
            # Google normally keeps the same refresh token, but may send a new one.
            "refresh_token": body.get("refresh_token") or saved["refresh_token"],
        }
        self.tokens.save(self._key, user_id, saved)
        return saved

    def _raise_for_error(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = ""
        detail = f" Google said: {detail[:300]}" if detail else ""
        if status == 401:
            raise MeetingError("reconnect_required", "Your Google connection has expired. Please connect again.")
        if status == 403:
            raise MeetingError(
                "permission_denied",
                "Google refused access. Check that the Google Meet API is turned on in your Google Cloud project "
                f"and that your Workspace plan includes Meet transcripts.{detail}",
            )
        if status == 404:
            raise MeetingError("meeting_not_found", "Google couldn't find that meeting. Its transcript may have been deleted after 30 days.")
        if status == 429:
            raise MeetingError("provider_rate_limited", "Google is limiting requests right now. Try again in a minute.")
        raise MeetingError("provider_error", f"Google returned an error ({status}).{detail}")
