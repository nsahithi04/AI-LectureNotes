"""Pieces shared by providers that connect accounts with OAuth 2.0 (Google, Microsoft).

A sign-in goes: LectureAI sends the teacher to the provider with a one-time "state" value, the provider
sends them back with that state and a code, and LectureAI swaps the code for tokens. The state ties the
callback to the teacher who started it, which stops another site from connecting its own account to them.
PKCE (a secret the browser never sees) means a stolen code can't be used by anyone else.
"""

import base64
import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.meetings.errors import MeetingError

STATE_LIFETIME_SECONDS = 600


@dataclass(frozen=True)
class PendingSignIn:
    provider: str
    user_id: str
    code_verifier: str
    expires_at: float


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class OAuthStateStore:
    """Sign-ins in progress. Kept in memory: a server restart only cancels sign-ins that take a minute anyway."""

    def __init__(self, max_pending: int = 1000, clock: Callable[[], float] = time.time):
        self.max_pending = max_pending
        self.clock = clock
        self._pending: dict[str, PendingSignIn] = {}
        self._lock = threading.Lock()

    def create(self, provider: str, user_id: str) -> tuple[str, str]:
        """Start a sign-in. Returns the state to send, and the PKCE code challenge."""
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        now = self.clock()
        with self._lock:
            self._pending = {key: value for key, value in self._pending.items() if value.expires_at > now}
            if len(self._pending) >= self.max_pending:
                oldest = min(self._pending, key=lambda key: self._pending[key].expires_at)
                del self._pending[oldest]
            self._pending[state] = PendingSignIn(provider, user_id, verifier, now + STATE_LIFETIME_SECONDS)
        return state, code_challenge(verifier)

    def consume(self, provider: str, state: Optional[str]) -> PendingSignIn:
        """Match a callback to its sign-in. Each state works once, for the provider that created it."""
        with self._lock:
            pending = self._pending.pop(state, None) if state else None
        if pending is None or pending.provider != provider or pending.expires_at <= self.clock():
            raise MeetingError("invalid_connection", "This sign-in link has expired or was already used. Please connect again.")
        return pending


def id_token_email(id_token: Optional[str]) -> Optional[str]:
    """The account's email address from an ID token, to show which account is connected.

    The token came straight from the provider over HTTPS, so its signature doesn't need checking here.
    It's only used as a label, never to decide who someone is.
    """
    if not id_token:
        return None
    try:
        payload = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return None
    email = claims.get("email") or claims.get("preferred_username")
    return email if isinstance(email, str) else None
