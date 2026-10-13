from datetime import datetime
from threading import RLock

from banking.domain.models import StoredSession


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, StoredSession] = {}
        self._lock = RLock()

    def save(self, token: str, session: StoredSession) -> None:
        with self._lock:
            self._sessions[token] = session

    def get(self, token: str) -> StoredSession | None:
        with self._lock:
            return self._sessions.get(token)

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def delete_expired(self, now: datetime) -> None:
        with self._lock:
            self._sessions = {
                token: session
                for token, session in self._sessions.items()
                if session.expires_at > now
            }
