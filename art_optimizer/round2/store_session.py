from __future__ import annotations

from typing import Sequence

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


class Round2SessionWriteMixin:
    def initialize_session(
        self,
        *,
        state: SessionState,
        assignment: TreatmentAssignment,
        scope: RepresentationScope,
        projection: IdealPointProjection,
        world_event_payload: dict[str, object],
    ) -> None:
        timestamp = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT INTO events(session_id, kind, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        state.session_id,
                        "world_created",
                        encode(world_event_payload),
                        timestamp,
                    ),
                )
                upsert_session(connection, state, timestamp)
                connection.execute(
                    """
                    INSERT INTO r2_treatment_assignments(
                        session_id, user_id, treatment_id,
                        assignment_json, scope_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state.session_id,
                        assignment.user_id,
                        assignment.treatment_id,
                        assignment.model_dump_json(),
                        scope.model_dump_json(),
                        timestamp,
                    ),
                )
                upsert_projection(connection, state.session_id, projection, timestamp)
                sequence = next_sequence(connection, assignment.user_id)
                event_id = f"event_treatment_{state.session_id.removeprefix('session_')}"
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
                        "TreatmentAssigned",
                        encode(
                            {
                                "event_id": event_id,
                                "event_sequence": sequence,
                                "session_id": state.session_id,
                                "treatment": assignment.model_dump(mode="json"),
                                "scope": scope.model_dump(mode="json"),
                            }
                        ),
                        timestamp,
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def save_projection(
        self,
        session_id: str,
        projection: IdealPointProjection,
    ) -> None:
        with self._lock, self._connect() as connection:
            upsert_projection(connection, session_id, projection, utc_now())

    def save_candidate_contexts(
        self,
        contexts: Sequence[CandidateContext],
    ) -> None:
        if not contexts:
            return
        timestamp = utc_now()
        with self._lock, self._connect() as connection:
            for context in contexts:
                upsert_context(connection, context, timestamp)

    def save_predictive_receipt(self, receipt: PredictiveReceipt) -> None:
        with self._lock, self._connect() as connection:
            insert_predictive_receipt(connection, receipt)

    def save_slate_receipt(self, receipt: PerceptualSlateReceipt) -> None:
        with self._lock, self._connect() as connection:
            upsert_slate_receipt(connection, receipt, utc_now())
