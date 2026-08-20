from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


CandidateRole = Literal[
    "best_local",
    "diverse_posterior",
    "informative_probe",
    "controlled_surprise",
]

CandidateStatus = Literal["queued", "rendering", "ready", "failed", "cancelled"]


class GaussianSnapshot(BaseModel):
    mean: list[float]
    covariance: list[list[float]]
    dimension: int
    feature_dimension: int
    observation_count: int = 0


class SearchState(BaseModel):
    radius: float = 0.55
    consecutive_rerolls: int = 0
    consecutive_commits: int = 0
    planner_step: int = 0


class DesignState(BaseModel):
    design_id: str
    world_id: str
    parent_design_id: str | None = None
    source_candidate_id: str | None = None
    seed: int
    prompt: str
    action: list[float]
    image_url: str
    image_path: str
    feature_vector: list[float]
    renderer_revision: str = "procedural-field/v1"
    control_basis_revision: str = "procedural-global-8d/v1"
    created_at: str = Field(default_factory=utc_now)


class BranchNode(BaseModel):
    branch_node_id: str
    design_id: str
    parent_branch_node_id: str | None = None
    posterior: GaussianSnapshot
    search_state: SearchState
    created_at: str = Field(default_factory=utc_now)


class CandidateProposal(BaseModel):
    candidate_id: str
    slot: int = Field(ge=1, le=4)
    role: CandidateRole
    action: list[float]
    expected_utility: float
    uncertainty: float
    status: CandidateStatus = "queued"
    design_id: str | None = None
    image_url: str | None = None
    error: str | None = None


class CandidateRound(BaseModel):
    round_id: str
    parent_design_id: str
    parent_branch_node_id: str
    branch_version: int
    candidates: list[CandidateProposal]
    status: Literal["rendering", "ready", "closed", "cancelled"] = "rendering"
    created_at: str = Field(default_factory=utc_now)


class WorldState(BaseModel):
    world_id: str
    seed: int
    prompt: str
    root_design_id: str
    atlas_component_id: str | None = None
    atlas_bias_action: list[float] | None = None
    created_at: str = Field(default_factory=utc_now)


class SessionState(BaseModel):
    session_id: str
    user_id: str = "local-user"
    version: int = 0
    prompt: str
    world: WorldState
    designs: dict[str, DesignState]
    branches: dict[str, BranchNode]
    current_design_id: str
    current_branch_node_id: str
    active_posterior: GaussianSnapshot
    search_state: SearchState
    active_round: CandidateRound | None = None
    favorites: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    status: Literal["ready", "generating", "error"] = "ready"
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)

    def current_design(self) -> DesignState:
        return self.designs[self.current_design_id]

    def touch(self) -> None:
        self.version += 1
        self.updated_at = utc_now()


class CreateSessionRequest(BaseModel):
    prompt: str = "an evolving impossible garden"
    seed: int | None = None


class ExposurePayload(BaseModel):
    exposed_candidate_ids: list[str] = Field(default_factory=list)


class CommitPayload(ExposurePayload):
    expected_version: int | None = None


class FavoritePayload(BaseModel):
    favorite: bool = True


class AtlasEvidence(BaseModel):
    evidence_id: str
    design_id: str
    feature_vector: list[float]
    action: list[float]
    kind: Literal["commit", "favorite", "revisit", "export"]
    weight: float
    active: bool = True
    created_at: str = Field(default_factory=utc_now)


class AtlasComponent(BaseModel):
    component_id: str
    centroid: list[float]
    variance: list[float]
    action_centroid: list[float]
    evidence_mass: float
    evidence_count: int
    proposal_weight: float
    exemplar_design_ids: list[str]
    last_activated_at: str = Field(default_factory=utc_now)
    status: Literal["active", "dormant"] = "active"


class PreferenceAtlasState(BaseModel):
    user_id: str = "local-user"
    components: list[AtlasComponent] = Field(default_factory=list)
    evidence: list[AtlasEvidence] = Field(default_factory=list)
    provisional: list[AtlasEvidence] = Field(default_factory=list)
    outside_prior_mass: float = 0.20
    revision: str = "atlas-online-mixture/v1"
    updated_at: str = Field(default_factory=utc_now)
