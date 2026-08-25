from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TasteDesignRef(ContractModel):
    design_id: str
    action: list[float]
    image_url: str = ""
    branch_node_id: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: list[float]) -> list[float]:
        vector = np.asarray(value, dtype=np.float64)
        if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
            raise ValueError("action must be a non-empty finite vector")
        return value


class TasteAlternative(TasteDesignRef):
    candidate_id: str
    slot: int = Field(ge=1, le=4)


class TasteChoiceObservation(ContractModel):
    """One fixed-root multi-choice fact and its before-outcome predictions."""

    observation_id: str
    request_id: str
    round_id: str
    seed: int = Field(ge=0)
    control_basis_revision: str
    representation_scope_id: str = ""
    representation_scope: dict[str, object] = Field(default_factory=dict)
    anchor: TasteDesignRef
    alternatives: list[TasteAlternative] = Field(min_length=1, max_length=4)
    winner_index: int = Field(ge=0, le=4)
    result_branch_node_id: str
    created_at: str
    observation_weight: float = Field(default=1.0, gt=0.0, le=1.0)
    prediction_receipts: dict[str, float] = Field(default_factory=dict)
    receipt_semantics: str = "legacy_probability"

    @model_validator(mode="after")
    def validate_slate(self) -> Self:
        dimension = len(self.anchor.action)
        if any(len(item.action) != dimension for item in self.alternatives):
            raise ValueError("every action in one observation must share a dimension")
        if self.winner_index > len(self.alternatives):
            raise ValueError("winner_index is outside the recorded choice set")
        candidate_ids = [item.candidate_id for item in self.alternatives]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate IDs must be unique")
        for key, evidence in self.prediction_receipts.items():
            if not key.startswith("k=") or not 0.0 < float(evidence) <= 1.0:
                raise ValueError("prediction receipts must be named evidence values in (0, 1]")
        if self.receipt_semantics not in {
            "legacy_probability",
            "power_evidence_v1",
        }:
            raise ValueError("unknown prediction receipt semantics")
        if not self.representation_scope_id:
            scope_id = self.representation_scope.get("scope_id")
            self.representation_scope_id = (
                str(scope_id) if scope_id else self.control_basis_revision
            )
        return self

    @property
    def dimension(self) -> int:
        return len(self.anchor.action)

    def action_matrix(self) -> np.ndarray:
        return np.asarray(
            [self.anchor.action, *[item.action for item in self.alternatives]],
            dtype=np.float64,
        )

    def winner(self) -> TasteDesignRef:
        if self.winner_index == 0:
            return self.anchor
        return self.alternatives[self.winner_index - 1]


@dataclass(slots=True)
class TasteFit:
    component_count: int
    centers: np.ndarray
    prevalence: np.ndarray
    responsibilities: np.ndarray
    filtered_state: np.ndarray
    effective_counts: np.ndarray
    log_likelihood: float
    objective: float
    converged: bool
    iterations: int


@dataclass(slots=True)
class TasteEngineState:
    observations: list[TasteChoiceObservation]
    fits: dict[int, TasteFit]
    log_scores: dict[int, float]
    prediction_counts: dict[int, int]
    selected_k: int
    scored_models: list[dict[str, object]]


def deterministic_observation_id(session_id: str, request_id: str) -> str:
    digest = hashlib.sha256(f"{session_id}:{request_id}".encode()).hexdigest()
    return f"taste_observation_{digest[:24]}"
