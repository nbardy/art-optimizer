from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .domain import PreferenceAtlasState, SessionState, utc_now


class EventStore:
    """Small SQLite event store with persisted session and atlas projections."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_session_id
                    ON events(session_id, event_id);

                CREATE TABLE IF NOT EXISTS session_projections (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS atlas_projections (
                    user_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def append_event(self, session_id: str, kind: str, payload: dict[str, Any]) -> int:
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events(session_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (session_id, kind, encoded, utc_now()),
            )
            return int(cursor.lastrowid)

    def record_session_event(
        self,
        state: SessionState,
        kind: str,
        payload: dict[str, Any],
    ) -> int:
        """Append an event and advance its projection in one SQLite transaction."""
        encoded_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        encoded_state = state.model_dump_json()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events(session_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (state.session_id, kind, encoded_payload, utc_now()),
            )
            connection.execute(
                """
                INSERT INTO session_projections(session_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (state.session_id, encoded_state, utc_now()),
            )
            return int(cursor.lastrowid)

    def save_session(self, state: SessionState) -> None:
        encoded = state.model_dump_json()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_projections(session_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (state.session_id, encoded, utc_now()),
            )

    def load_session(self, session_id: str) -> SessionState | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM session_projections WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionState.model_validate_json(row["state_json"])

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id, kind, payload_json, created_at FROM events WHERE session_id = ? ORDER BY event_id",
                (session_id,),
            ).fetchall()
        return [
            {
                "event_id": int(row["event_id"]),
                "kind": row["kind"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_atlas(self, state: PreferenceAtlasState) -> None:
        encoded = state.model_dump_json()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO atlas_projections(user_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (state.user_id, encoded, utc_now()),
            )

    def load_atlas(self, user_id: str = "local-user") -> PreferenceAtlasState:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM atlas_projections WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return PreferenceAtlasState(user_id=user_id)
        return PreferenceAtlasState.model_validate_json(row["state_json"])
