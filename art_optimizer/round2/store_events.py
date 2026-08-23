from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ..domain import SessionState, utc_now
from .contracts import (
    CandidateContext,
    IdealPointProjection,
    PerceptualSlateReceipt,
    PredictiveReceipt,
    RepresentationScope,
    TreatmentAssignment,
)
from .store_schema import (
    encode,
    insert_predictive_receipt,
    next_sequence,
    upsert_context,
    upsert_projection,
    upsert_session,
    upsert_slate_receipt,
)


class Round2EventWriteMixin:
    def record_round_event(
        self,
        *,
        state: SessionState,
        kind: str,
        payload: dict[str, Any],
        contexts: Sequence[CandidateContext] = (),
        slate_receipt: PerceptualSlateReceipt | None = None,
        predictive_receipt: PredictiveReceipt | None = None,
    ) -> int:
        timestamp = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO events(session_id, kind, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (state.session_id, kind, encode(payload), timestamp),
                )
                upsert_session(connection, state, timestamp)
                for context in contexts:
                    upsert_context(connection, context, timestamp)
                if slate_receipt is not None:
                    upsert_slate_receipt(connection, slate_receipt, timestamp)
                if predictive_receipt is not None:
                    insert_predictive_receipt(connection, predictive_receipt)
                connection.commit()
                return int(cursor.lastrowid)
            except Exception:
                connection.rollback()
                raise

    def record_command(
        self,
        *,
        state: SessionState,
        assignment: TreatmentAssignment,
        scope: RepresentationScope,
        command_kind: str,
        request_id: str,
        event_id: str,
        event_kind: str,
        event_payload: dict[str, Any],
        result: dict[str, Any],
        projections: Mapping[str, IdealPointProjection] | None = None,
        contexts: Sequence[CandidateContext] = (),
    ) -> tuple[dict[str, Any], int | None]:
        timestamp = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    """
                    SELECT kind, result_json FROM command_results
                    WHERE session_id = ? AND request_id = ?
                    """,
                    (state.session_id, request_id),
                ).fetchone()
                if existing is not None:
                    if existing["kind"] != command_kind:
                        raise ValueError(
                            "request_id was already used for a different command"
                        )
                    connection.rollback()
                    return json.loads(existing["result_json"]), None

                sequence = next_sequence(connection, assignment.user_id)
                canonical_payload = {
                    **event_payload,
                    "event_id": event_id,
                    "event_sequence": sequence,
                    "schema_revision": "round2-interaction-event/v1",
                    "user_id": assignment.user_id,
                    "session_id": state.session_id,
                    "treatment_id": assignment.treatment_id,
                    "scope_id": scope.scope_id,
                    "created_at": timestamp,
                }
                connection.execute(
                    """
                    INSERT INTO r2_interaction_events(
                        event_id, user_id, event_sequence, session_id,
                        treatment_id, scope_id, kind, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        assignment.user_id,
                        sequence,
                        state.session_id,
                        assignment.treatment_id,
                        scope.scope_id,
                        event_kind,
                        encode(canonical_payload),
                        timestamp,
                    ),
                )
                upsert_session(connection, state, timestamp)
                for projection in (projections or {}).values():
                    upsert_projection(connection, state.session_id, projection, timestamp)
                for context in contexts:
                    upsert_context(connection, context, timestamp)
                connection.execute(
                    """
                    INSERT INTO command_results(
                        session_id, request_id, kind, result_json, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        state.session_id,
                        request_id,
                        command_kind,
                        encode(result),
                        timestamp,
                    ),
                )
                connection.commit()
                return result, sequence
            except Exception:
                connection.rollback()
                raise
