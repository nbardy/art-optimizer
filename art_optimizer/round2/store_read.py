from __future__ import annotations

import json
from typing import Any

from .contracts import (
    CandidateContext,
    IdealPointProjection,
    PerceptualSlateReceipt,
    PredictiveReceipt,
    RepresentationScope,
    TreatmentAssignment,
)


class Round2ReadMixin:
    def load_assignment(self, session_id: str) -> TreatmentAssignment | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT assignment_json FROM r2_treatment_assignments WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return None if row is None else TreatmentAssignment.model_validate_json(
            row["assignment_json"]
        )

    def load_scope(self, session_id: str) -> RepresentationScope | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT scope_json FROM r2_treatment_assignments WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return None if row is None else RepresentationScope.model_validate_json(
            row["scope_json"]
        )

    def load_projection(
        self,
        session_id: str,
        engine_id: str,
    ) -> IdealPointProjection | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT projection_json FROM r2_engine_projections
                WHERE session_id = ? AND engine_id = ?
                """,
                (session_id, engine_id),
            ).fetchone()
        return None if row is None else IdealPointProjection.model_validate_json(
            row["projection_json"]
        )

    def load_candidate_context(self, candidate_id: str) -> CandidateContext | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT context_json FROM r2_candidate_contexts WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        return None if row is None else CandidateContext.model_validate_json(
            row["context_json"]
        )

    def load_round_contexts(
        self,
        session_id: str,
        round_id: str,
    ) -> dict[str, CandidateContext]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT candidate_id, context_json FROM r2_candidate_contexts
                WHERE session_id = ? AND round_id = ? ORDER BY candidate_id
                """,
                (session_id, round_id),
            ).fetchall()
        return {
            row["candidate_id"]: CandidateContext.model_validate_json(row["context_json"])
            for row in rows
        }

    def latest_predictive_receipt(
        self,
        session_id: str,
        round_id: str,
        engine_id: str,
    ) -> PredictiveReceipt | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_json FROM r2_predictive_receipts
                WHERE session_id = ? AND round_id = ? AND engine_id = ?
                ORDER BY created_at DESC, receipt_id DESC LIMIT 1
                """,
                (session_id, round_id, engine_id),
            ).fetchone()
        return None if row is None else PredictiveReceipt.model_validate_json(
            row["receipt_json"]
        )

    def load_slate_receipt(
        self,
        session_id: str,
        round_id: str,
    ) -> PerceptualSlateReceipt | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_json FROM r2_slate_receipts
                WHERE session_id = ? AND round_id = ?
                """,
                (session_id, round_id),
            ).fetchone()
        return None if row is None else PerceptualSlateReceipt.model_validate_json(
            row["receipt_json"]
        )

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, event_sequence, kind, payload_json, created_at
                FROM r2_interaction_events
                WHERE session_id = ? ORDER BY event_sequence
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "event_sequence": int(row["event_sequence"]),
                "kind": row["kind"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
