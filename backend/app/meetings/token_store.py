"""Where connected accounts' OAuth tokens are kept.

DEVELOPMENT ONLY. Tokens are stored unencrypted in one JSON file that only this computer's user can read.
Production must keep them encrypted in a database, tied to authenticated LectureAI users. Never log tokens.
"""

import json
import os
import threading
from pathlib import Path
from typing import Optional, Protocol


class TokenStore(Protocol):
    def save(self, provider: str, user_id: str, tokens: dict) -> None: ...
    def get(self, provider: str, user_id: str) -> Optional[dict]: ...
    def delete(self, provider: str, user_id: str) -> None: ...
    def connected_providers(self, user_id: str) -> list[str]: ...


class DevFileTokenStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def _read(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.is_file() else {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        # Readable and writable by this computer's user only.
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump(data, out)
        os.replace(temp, self.path)

    def save(self, provider: str, user_id: str, tokens: dict) -> None:
        with self._lock:
            data = self._read()
            data.setdefault(user_id, {})[provider] = tokens
            self._write(data)

    def get(self, provider: str, user_id: str) -> Optional[dict]:
        return self._read().get(user_id, {}).get(provider)

    def delete(self, provider: str, user_id: str) -> None:
        with self._lock:
            data = self._read()
            data.get(user_id, {}).pop(provider, None)
            self._write(data)

    def connected_providers(self, user_id: str) -> list[str]:
        return sorted(self._read().get(user_id, {}))
