from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from ..domain import (
    MAX_SEED,
    CommandPayload,
    ContractModel,
    ExposurePayload,
    new_id,
    utc_now,
)

TRUTHFUL_SEARCH_TREATMENT_ID = "r2-truthful-search-v1"
T0_TREATMENT_ID = "t0-controlled-search-v0"

SeedRelation = Literal["same_root", "fresh_root"]
WinnerKind = Literal["anchor", "candidate"]


class RepresentationScope(ContractModel):
    """Exact numeric-coordinate compatibility boundary for one session."""

    scope_id: str
    model_id: str
    model_source: str
    model_revision: str
    renderer_revision: str
    control_codec_revision: str
    control_basis_revision: str
    direction_bank_digest: str
    prompt_digest: str
    prompt_scope_id: str
    action_dimension: int = Field(ge=1, le=16)
    conditioning_mode: str
    portable: bool = False
    manifest_revision: str = "representation-scope/v1"

    def public_summary(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "renderer_revision": self.renderer_revision,
            "control_codec_revision": self.control_codec_revision,
            "control_basis_revision": self.control_basis_revision,
            "direction_bank_digest": self.direction_bank_digest,
            "prompt_digest": self.prompt_digest,
            "action_dimension": self.action_dimension,
            "conditioning_mode": self.conditioning_mode,
            "portable": self.portable,
            "manifest_revision": self.manifest_revision,
        }


class TreatmentAssignment(ContractModel):
    session_id: str
    user_id: str = "local-user"
    treatment_id: str
    treatment_revision: str = "truthful-search-policy/v1"
    observation_contract: str = "exposed-multichoice-with-neutral-novelty/v1"
    authoritative_engine_id: str = "legacy-quadratic-44d"
    authoritative_engine_revision: str = "laplace-mnl-truthful/v1"
    shadow_engine_ids: list[str] = Field(default_factory=lambda: ["ideal-point-8d"])
    planner_revision: str = "finite-pool-four-role-hybrid-root/v1"
    noise_policy_revision: str = "hybrid-common-and-fresh-root/v1"
    perceptual_policy_revision: str = "handcrafted-output-embedding-dedup/v1"
    ui_id: str = "truthful-search"
    assigned_at: str = Field(default_factory=utc_now)


class CandidateContext(ContractModel):
    candidate_id: str
    design_id: str
    session_id: str
    round_id: str
    world_id: str
    scope_id: str
    seed: int = Field(ge=0, le=MAX_SEED)
    seed_relation: SeedRelation
    root_noise_digest: str
    prompt_digest: str
    comparison_context_digest: str
    role: str
    slot: int = Field(ge=1, le=4)
    perceptual_embedding: list[float] | None = None
    perceptual_revision: str | None = None
    perceptual_equivalence_class: str | None = None
    duplicate_of: str | None = None
    repair_count: int = Field(default=0, ge=0, le=3)
    created_at: str = Field(default_factory=utc_now)

    @field_validator("perceptual_embedding")
    @classmethod
    def validate_embedding(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and not value:
            raise ValueError("perceptual embedding cannot be empty")
        return value


class ChoiceAlternative(ContractModel):
    candidate_id: str
    design_id: str
    action: list[float]
    slot: int = Field(ge=1, le=4)
    role: str
    seed: int = Field(ge=0, le=MAX_SEED)
    seed_relation: SeedRelation
    world_id: str
    root_noise_digest: str
    comparison_context_digest: str
    image_digest: str
    perceptual_equivalence_class: str | None = None


class QualificationReceipt(ContractModel):
    qualified: bool
    revision: str = "same-context-exposure-qualification/v1"
    exposed_candidate_ids: list[str]
    qualified_candidate_ids: list[str]
    excluded_candidate_reasons: dict[str, list[str]] = Field(default_factory=dict)
    minimum_required: int = Field(default=1, ge=1)
    reason: str


class PredictiveReceipt(ContractModel):
    receipt_id: str = Field(default_factory=lambda: new_id("prediction"))
    session_id: str
    round_id: str
    treatment_id: str
    engine_id: str
    engine_revision: str
    projection_revision: str
    scope_id: str
    alternative_ids: list[str]
    probabilities: list[float]
    entropy: float = Field(ge=0.0)
    source_event_cursor_digest: str
    approximation_revision: str
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_probability_shape(self) -> "PredictiveReceipt":
        if len(self.alternative_ids) != len(self.probabilities):
            raise ValueError("predictive receipt IDs and probabilities must align")
        if not self.probabilities:
            raise ValueError("predictive receipt must contain alternatives")
        total = sum(self.probabilities)
        if any(value < 0.0 or value > 1.0 for value in self.probabilities):
            raise ValueError("predictive probabilities must lie in [0, 1]")
        if abs(total - 1.0) > 1e-6:
            raise ValueError("predictive probabilities must sum to one")
        return self


class PerceptualSlateReceipt(ContractModel):
    session_id: str
    round_id: str
    revision: str
    candidate_ids: list[str]
    distance_matrix: list[list[float]]
    anchor_distances: dict[str, float]
    equivalence_classes: dict[str, str]
    duplicate_of: dict[str, str]
    repaired_candidate_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class IdealPointObservation(ContractModel):
    event_id: str
    scope_id: str
    alternative_ids: list[str]
    actions: list[list[float]]
    chosen_index: int = Field(ge=0)
    weight: float = Field(gt=0.0)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_observation(self) -> "IdealPointObservation":
        if len(self.alternative_ids) != len(self.actions):
            raise ValueError("alternative IDs and actions must align")
        if len(self.actions) < 2:
            raise ValueError("choice observation requires at least two alternatives")
        dimension = len(self.actions[0])
        if dimension < 1:
            raise ValueError("actions must be non-empty")
        if any(len(action) != dimension for action in self.actions):
            raise ValueError("all actions must have the same dimension")
        if self.chosen_index >= len(self.actions):
            raise ValueError("chosen index is outside the alternatives")
        return self


class IdealPointProjection(ContractModel):
    engine_id: str = "ideal-point-8d"
    engine_revision: str = "joint-map-laplace/v1"
    projection_schema_revision: str = "ideal-point-projection/v1"
    scope_id: str
    dimension: int = Field(ge=1, le=16)
    prior_mean: list[float]
    prior_covariance: list[list[float]]
    posterior_mean: list[float]
    posterior_covariance: list[list[float]]
    utility_curvature: list[list[float]]
    temperature: float = Field(gt=0.0)
    observations: list[IdealPointObservation] = Field(default_factory=list)
    effective_evidence_mass: float = Field(default=0.0, ge=0.0)
    source_event_cursor_digest: str
    optimizer_receipt: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=utc_now)

    @property
    def observation_count(self) -> int:
        return len(self.observations)


class MoreVarietyPayload(ExposurePayload):
    pass


class NoneOfThesePayload(ExposurePayload):
    pass


class BrokenRenderPayload(CommandPayload):
    reason: str = Field(default="broken_or_irrelevant", min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())


class TreatmentDescriptor(ContractModel):
    treatment_id: str
    label: str
    description: str
    implemented: bool
    ui_id: str
    authoritative_engine_id: str
    shadow_engine_ids: list[str]
