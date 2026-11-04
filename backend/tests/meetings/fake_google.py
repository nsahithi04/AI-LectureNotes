"""A pretend Google: its OAuth token endpoint and the parts of the Meet REST API LectureAI uses.

It checks requests the way Google does (the bearer token, the PKCE verifier) so tests catch mistakes.
"""

import base64
import json
from urllib.parse import parse_qs

import httpx

from app.meetings.oauth import code_challenge

CLIENT_ID = "test-client.apps.googleusercontent.com"
MEET_SCOPE = "https://www.googleapis.com/auth/meetings.space.readonly"


def id_token(email):
    payload = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).rstrip(b"=").decode()
    return f"header.{payload}.signature"


class FakeGoogle:
    def __init__(self):
        self.challenges = {}           # authorization code -> PKCE challenge it was issued with
        self.granted_scope = f"openid email {MEET_SCOPE}"
        self.access_token = "access-1"
        self.refresh_count = 0
        self.refresh_fails = False
        self.revoked = []
        self.requests = []
        self.errors = {}               # path -> (status, message) to return instead
        self.records = {}              # record id -> conference record
        self.transcripts = {}          # record id -> list of transcripts
        self.entries = {}              # transcript name -> list of entries
        self.participants = {}         # record id -> list of participants
        self.spaces = {}               # space name -> space
        self.entries_page_size_seen = []

    def issue_code(self, challenge, code="auth-code"):
        self.challenges[code] = challenge
        return code

    def transport(self):
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host, path = request.url.host, request.url.path
        if host == "oauth2.googleapis.com" and path == "/token":
            return self.token(parse_qs(request.content.decode()))
        if host == "oauth2.googleapis.com" and path == "/revoke":
            self.revoked.append(parse_qs(request.content.decode())["token"][0])
            return httpx.Response(200)
        if host == "meet.googleapis.com":
            if request.headers.get("Authorization") != f"Bearer {self.access_token}":
                return httpx.Response(401, json={"error": {"message": "Invalid credentials"}})
            return self.meet(path.removeprefix("/v2/"), request.url.params)
        return httpx.Response(404)

    def token(self, form):
        field = lambda name: form.get(name, [None])[0]
        if field("client_id") != CLIENT_ID or field("client_secret") != "test-secret":
            return httpx.Response(401, json={"error": "invalid_client"})
        if field("grant_type") == "authorization_code":
            challenge = self.challenges.pop(field("code"), None)
            if challenge is None or code_challenge(field("code_verifier")) != challenge:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(
                200,
                json={
                    "access_token": self.access_token,
                    "expires_in": 3599,
                    "refresh_token": "refresh-1",
                    "scope": self.granted_scope,
                    "id_token": id_token("teacher@school.edu"),
                },
            )
        if field("grant_type") == "refresh_token":
            if self.refresh_fails or field("refresh_token") != "refresh-1":
                return httpx.Response(400, json={"error": "invalid_grant"})
            self.refresh_count += 1
            self.access_token = f"access-{self.refresh_count + 1}"
            return httpx.Response(200, json={"access_token": self.access_token, "expires_in": 3599})
        return httpx.Response(400, json={"error": "unsupported_grant_type"})

    def meet(self, path, params):
        if path in self.errors:
            status, message = self.errors[path]
            return httpx.Response(status, json={"error": {"message": message}})
        parts = path.split("/")
        if path == "conferenceRecords":
            records = sorted(self.records.values(), key=lambda r: r["startTime"], reverse=True)
            return httpx.Response(200, json={"conferenceRecords": records[: int(params.get("pageSize", 25))]})
        if parts[0] == "spaces" and path in self.spaces:
            return httpx.Response(200, json=self.spaces[path])
        if parts[0] != "conferenceRecords" or parts[1] not in self.records:
            return httpx.Response(404, json={"error": {"message": "Not found"}})
        record_id = parts[1]
        if len(parts) == 2:
            return httpx.Response(200, json=self.records[record_id])
        if parts[2:] == ["transcripts"]:
            return httpx.Response(200, json={"transcripts": self.transcripts.get(record_id, [])})
        if parts[2:] == ["participants"]:
            return httpx.Response(200, json={"participants": self.participants.get(record_id, [])})
        if len(parts) == 5 and parts[2] == "transcripts" and parts[4] == "entries":
            return self.paged(self.entries.get("/".join(parts[:4]), []), params)
        return httpx.Response(404, json={"error": {"message": "Not found"}})

    def paged(self, entries, params):
        size = int(params.get("pageSize", 10))
        self.entries_page_size_seen.append(size)
        start = int(params.get("pageToken", 0))
        body = {"transcriptEntries": entries[start : start + size]}
        if start + size < len(entries):
            body["nextPageToken"] = str(start + size)
        return httpx.Response(200, json=body)
