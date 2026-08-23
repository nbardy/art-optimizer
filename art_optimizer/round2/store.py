from __future__ import annotations

import sqlite3
import threading

from ..event_store import EventStore
from .store_events import Round2EventWriteMixin
from .store_read import Round2ReadMixin
from .store_schema import initialize_schema
from .store_session import Round2SessionWriteMixin


class Round2Store(
    Round2ReadMixin,
    Round2SessionWriteMixin,
    Round2EventWriteMixin,
):
    """Namespaced Round 2 facts and projections in the existing SQLite database."""

    def __init__(self, base_store: EventStore) -> None:
        self.base_store = base_store
        self._lock = threading.RLock()
        with self._lock, self._connect() as connection:
            initialize_schema(connection)

    def _connect(self) -> sqlite3.Connection:
        return self.base_store._connect()  # noqa: SLF001 - same-package storage extension
