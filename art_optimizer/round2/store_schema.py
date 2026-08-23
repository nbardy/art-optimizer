from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..domain import SessionState
from .contracts import (
    CandidateContext,
    IdealPointProjection,
    PerceptualSlateReceipt,
    PredictiveReceipt,
)


def encode(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS r2_treatment_assignments (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            treatment_id TEXT NOT NULL,
            assignment_json TEXT NOT NULL,
            scope_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_r2_treatments_user
            ON r2_treatment_assignments(user_id, treatment_id);

        CREATE TABLE IF NOT EXISTS r2_interaction_events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_sequence INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            treatment_id TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, event_sequence)
        );
        CREATE INDEX IF NOT EXISTS idx_r2_events_session
            ON r2_interaction_events(session_id, event_sequence);
        CREATE INDEX IF NOT EXISTS idx_r2_events_user
            ON r2_interaction_events(user_id, event_sequence);

        CREATE TABLE IF NOT EXISTS r2_engine_projections (
            session_id TEXT NOT NULL,
            engine_id TEXT NOT NULL,
            projection_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(session_id, engine_id)
        );

        CREATE TABLE IF NOT EXISTS r2_candidate_contexts (
            candidate_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            round_id TEXT NOT NULL,
            context_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_r2_contexts_round
            ON r2_candidate_contexts(session_id, round_id);

        CREATE TABLE IF NOT EXISTS r2_predictive_receipts (
            receipt_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            round_id TEXT NOT NULL,
            engine_id TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_r2_predictions_round
            ON r2_predictive_receipts(session_id, round_id, engine_id, created_at);

        CREATE TABLE IF NOT EXISTS r2_slate_receipts (
            session_id TEXT NOT NULL,
            round_id TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(session_id, round_id)
        );
        """
    )


def next_sequence(connection: sqlite3.Connection, user_id: str) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(event_sequence), 0) AS last_sequence
        FROM r2_interaction_events
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return int(row["last_sequence"]) + 1


def upsert_session(
    connection: sqlite3.Connection,
    state: SessionState,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO session_projections(session_id, state_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            state_json=excluded.state_json,
            updated_at=excluded.updated_at
        """,
        (state.session_id, state.model_dump_json(), timestamp),
    )


def upsert_projection(
    connection: sqlite3.Connection,
    session_id: str,
    projection: IdealPointProjection,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO r2_engine_projections(
            session_id, engine_id, projection_json, updated_at
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id, engine_id) DO UPDATE SET
            projection_json=excluded.projection_json,
            updated_at=excluded.updated_at
        """,
        (session_id, projection.engine_id, projection.model_dump_json(), timestamp),
    )


def upsert_context(
    connection: sqlite3.Connection,
    context: CandidateContext,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO r2_candidate_contexts(
            candidate_id, session_id, round_id, context_json, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id) DO UPDATE SET
            session_id=excluded.session_id,
            round_id=excluded.round_id,
            context_json=excluded.context_json,
            updated_at=excluded.updated_at
        """,
        (
            context.candidate_id,
            context.session_id,
            context.round_id,
            context.model_dump_json(),
            timestamp,
        ),
    )


def insert_predictive_receipt(
    connection: sqlite3.Connection,
    receipt: PredictiveReceipt,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO r2_predictive_receipts(
            receipt_id, session_id, round_id, engine_id,
            receipt_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            receipt.receipt_id,
            receipt.session_id,
            receipt.round_id,
            receipt.engine_id,
            receipt.model_dump_json(),
            receipt.created_at,
        ),
    )


def upsert_slate_receipt(
    connection: sqlite3.Connection,
    receipt: PerceptualSlateReceipt,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO r2_slate_receipts(
            session_id, round_id, receipt_json, updated_at
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id, round_id) DO UPDATE SET
            receipt_json=excluded.receipt_json,
            updated_at=excluded.updated_at
        """,
        (receipt.session_id, receipt.round_id, receipt.model_dump_json(), timestamp),
    )
