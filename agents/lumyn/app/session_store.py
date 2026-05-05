from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock

from .schemas import SessionRecord, SessionSummary, SessionTurn


class SessionStore:
    def __init__(self) -> None:
        self._items: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def get_or_create(self, session_id: str) -> SessionRecord:
        with self._lock:
            item = self._items.get(session_id)
            if item is None:
                item = SessionRecord(session_id=session_id)
                self._items[session_id] = item
            return item

    def append_turn(self, session_id: str, turn: SessionTurn) -> SessionRecord:
        with self._lock:
            session = self.get_or_create(session_id)
            session.turns.append(turn)
            session.updated_at = datetime.now(timezone.utc)
            return session

    def list_active(self) -> list[SessionSummary]:
        with self._lock:
            return [
                SessionSummary(
                    session_id=s.session_id,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    turns=len(s.turns),
                )
                for s in self._items.values()
            ]

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._items.pop(session_id, None) is not None

    def all(self) -> list[SessionRecord]:
        with self._lock:
            return list(self._items.values())

    def sessions_since(self, hours: int) -> list[SessionRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self._lock:
            return [s for s in self._items.values() if s.updated_at >= cutoff]
