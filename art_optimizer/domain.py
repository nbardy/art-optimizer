from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_SEED = (1 << 63) - 1


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _all_finite(values: list[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CandidateRole = Literal[
    "best_local",
    "diverse_posterior",
    "informative_probe",
    "controlled_surprise",
]

CandidateStatus = Literal["queued", "rendering", "ready", "failed", "cancelled"]


class GaussianSnapshot(ContractModel):
    mean: list[float]
    covariance: list[list[float]]
    dimension: int = Field(ge=1, le=16)
    feature_dimension: int = Field(ge=1, le=512)
    observation_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_shape_and_values(self) -> Self:
        if len(self.mean) != self.feature_dimension:
            raise ValueError("posterior mean has the wrong feature dimension")
        if len(self.covariance) != self.feature_dimension:
            raise ValueError("posterior covariance has the wrong row count")
        if any(len(row) != self.feature_dimension for row in self.covariance):
            raise ValueError("posterior covariance must be square")
        if not _all_finite(self.mean) or any(not _all_finite(row) for row in self.covariance):
            raise ValueError("posterior contains non-finite values")
        return self


class SearchState(ContractModel):
    radius: float = Field(default=0.55, ge=0.05, le=1.5)
    consecutive_rerolls: int = Field(default=0, ge=0)
    consecutive_commits: int = Field(default=0, ge=0)
    planner_step: int = Field(default=0, ge=0)


class DesignState(ContractModel):
    design_id: str
    world_id: str
    parent_design_id: str | None = None
    source_candidate_id: str | None = None
    seed: int = Field(ge=0, le=MAX_SEED)
    prompt: str
    action: list[float]
    image_url: str
    image_path: str
    image_digest: str = ""
    feature_vector: list[float]
    feature_revision: str = "procedural-features-13d/v1"
    renderer_revision: str = "procedural-field/v2"
    control_basis_revision: str = "procedural-global-8d/v1"
    created_at: str = Field(default_factory=utc_now)

    @field_validator("action", "feature_vector")
    @classmethod
    def validate_finite_vector(cls, value: list[float]) -> list[float]:
        if not value or not _all_finite(value):
            raise ValueError("vector must be non-empty and finite")
        return value


class BranchNode(ContractModel):
    branch_node_id: str
    design_id: str
    parent_branch_node_id: str | None = None
    posterior: GaussianSnapshot
    search_state: SearchState
    created_at: str = Field(default_factory=utc_now)


class CandidateProposal(ContractModel):
    candidate_id: str
    slot: int = Field(ge=1, le=4)
    role: CandidateRole
    action: list[float]
    expected_utility: float
    uncertainty: float = Field(ge=0.0)
    status: CandidateStatus = "queued"
    design_id: str | None = None
    image_url: str | None = None
    error: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: list[float]) -> list[float]:
        if not value or not _all_finite(value):
            raise ValueError("candidate action must be non-empty and finite")
        return value


class CandidateRound(ContractModel):
    round_id: str
    parent_design_id: str
    parent_branch_node_id: str
    branch_version: int = Field(ge=0)
    planner_seed: int = Field(default=0, ge=0, le=MAX_SEED)
    candidates: list[CandidateProposal]
    status: Literal["rendering", "ready", "closed", "cancelled"] = "rendering"
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_slate(self) -> Self:
        if len(self.candidates) != 4:
            raise ValueError("a v0 round must contain exactly four candidates")
        slots = [candidate.slot for candidate in self.candidates]
        if sorted(slots) != [1, 2, 3, 4]:
            raise ValueError("candidate slots must be exactly 1, 2, 3, and 4")
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")
        return self


class WorldState(ContractModel):
    world_id: str
    seed: int = Field(ge=0, le=MAX_SEED)
    prompt: str
    root_design_id: str
    renderer_revision: str = "procedural-field/v2"
    control_basis_revision: str = "procedural-global-8d/v1"
    atlas_component_id: str | None = None
    atlas_bias_action: list[float] | None = None
    created_at: str = Field(default_factory=utc_now)


class SessionState(ContractModel):
    session_id: str
    user_id: str = "local-user"
    # `version` changes for every visible projection update. `mutation_version`
    # changes only for branch/world commands and is safe for optimistic writes.
    version: int = Field(default=0, ge=0)
    mutation_version: int = Field(default=0, ge=0)
    prompt: str
    world: WorldState
    worlds: dict[str, WorldState] = Field(default_factory=dict)
    designs: dict[str, DesignState]
    branches: dict[str, BranchNode]
    current_design_id: str
    current_branch_node_id: str
    active_posterior: GaussianSnapshot
    search_state: SearchState
    active_round: CandidateRound | None = None
    favorites: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    status: Literal["ready", "generating", "transitioning", "error"] = "ready"
    transition_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def normalize_world_registry(self) -> Self:
        if self.world.world_id not in self.worlds:
            self.worlds[self.world.world_id] = self.world.model_copy(deep=True)
        return self

    def current_design(self) -> DesignState:
        return self.designs[self.current_design_id]

    def touch(self, *, mutation: bool = False) -> None:
        self.version += 1
        if mutation:
            self.mutation_version += 1
        self.updated_at = utc_now()


class CreateSessionRequest(ContractModel):
    prompt: str = Field(default="an evolving impossible garden", min_length=1, max_length=2_000)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("prompt cannot be blank")
        return normalized


class CommandPayload(ContractModel):
    request_id: str = Field(default_factory=lambda: new_id("command"), min_length=8, max_length=128)
    expected_mutation_version: int | None = Field(default=None, ge=0)
    # Kept for clients produced by the initial runnable branch.
    expected_version: int | None = Field(default=None, ge=0)

    def resolved_expected_mutation_version(self) -> int | None:
        if self.expected_mutation_version is not None:
            return self.expected_mutation_version
        return self.expected_version


class ExposurePayload(CommandPayload):
    exposed_candidate_ids: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("exposed_candidate_ids")
    @classmethod
    def unique_candidate_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class CommitPayload(ExposurePayload):
    pass


class FavoritePayload(CommandPayload):
    favorite: bool = True


class NewWorldPayload(CommandPayload):
    pass


class RestorePayload(CommandPayload):
    pass


class AtlasEvidence(ContractModel):
    evidence_id: str
    design_id: str
    feature_vector: list[float]
    action: list[float]
    kind: Literal["commit", "favorite", "revisit", "export"]
    weight: float = Field(gt=0.0)
    feature_revision: str = "procedural-features-13d/v1"
    control_basis_revision: str = "procedural-global-8d/v1"
    renderer_revision: str = "procedural-field/v2"
    active: bool = True
    created_at: str = Field(default_factory=utc_now)


class AtlasComponent(ContractModel):
    component_id: str
    centroid: list[float]
    variance: list[float]
    action_centroid: list[float]
    feature_revision: str = "procedural-features-13d/v1"
    control_basis_revision: str = "procedural-global-8d/v1"
    evidence_mass: float = Field(ge=0.0)
    evidence_count: int = Field(ge=1)
    proposal_weight: float = Field(ge=0.0, le=1.0)
    exemplar_design_ids: list[str]
    last_activated_at: str = Field(default_factory=utc_now)
    status: Literal["active", "dormant"] = "active"


class PreferenceAtlasState(ContractModel):
    user_id: str = "local-user"
    components: list[AtlasComponent] = Field(default_factory=list)
    evidence: list[AtlasEvidence] = Field(default_factory=list)
    provisional: list[AtlasEvidence] = Field(default_factory=list)
    outside_prior_mass: float = Field(default=0.20, ge=0.0, le=0.9)
    revision: str = "atlas-online-mixture/v2"
    updated_at: str = Field(default_factory=utc_now)
