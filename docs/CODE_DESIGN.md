# Code Design

**Status:** Proposed implementation design  
**Last updated:** 2026-08-19

## 1. Objective

This document turns the product and research ideas into an executable code shape. It does not claim that the implementation exists yet.

The first vertical slice should prove one complete loop:

```text
create a world
→ render one committed design
→ generate four candidate descendants
→ preview without committing
→ commit one candidate or reroll
→ star, reset, and restore history
→ reproduce every committed state
```

The main engineering rule is:

> The current design is an immutable generative state. A PNG is one rendering of that state, not the state itself.

## 2. Proposed repository layout

```text
art-optimizer/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── docs/
│   ├── UI_DESIGN.md
│   ├── RESEARCH_NOTES.md
│   ├── ARCHITECTURE.md
│   └── CODE_DESIGN.md
├── apps/
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── domain/
│       │   ├── state/
│       │   ├── transport/
│       │   └── test/
│       └── package.json
├── python/
│   ├── art_optimizer/
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── persistence/
│   │   ├── optimizer/
│   │   ├── renderer/
│   │   ├── features/
│   │   └── telemetry/
│   ├── tests/
│   └── pyproject.toml
├── packages/
│   └── contracts/
│       ├── schemas/
│       └── generated-typescript/
├── scripts/
│   ├── generate_contracts.py
│   ├── simulate_user.py
│   └── verify_replay.py
├── fixtures/
│   ├── sessions/
│   ├── optimizer/
│   └── renderer/
├── migrations/
└── .github/workflows/
```

Recommended initial tooling:

- React, TypeScript, Vite, and a small explicit reducer for the browser;
- Python 3.12+, FastAPI, Pydantic v2, and SQLAlchemy for the control plane;
- PyTorch, GPyTorch, and BoTorch for research implementations of preferential optimization;
- Diffusers or a model-native runtime behind a renderer adapter;
- SQLite and local files for development;
- PostgreSQL, object storage, and a priority queue only when deployment needs them;
- `uv` for Python and `pnpm` for TypeScript;
- pytest, Vitest, and Playwright for tests.

These are implementation defaults rather than permanent product contracts.

## 3. Package boundaries

### 3.1 `domain`

Pure types, invariants, events, commands, and reducers. It must not import FastAPI, SQLAlchemy, BoTorch, Diffusers, or browser code.

### 3.2 `application`

Command handlers and orchestration. It loads domain state, applies transitions, persists events, and emits generation or optimization jobs.

### 3.3 `optimizer`

Preference models, action proposal, trust regions, diversity selection, simulated users, and experiment metrics. BoTorch-specific tensors remain behind interfaces.

### 3.4 `renderer`

Model adapters, capability negotiation, deterministic noise materialization, render planning, batching, and progress streaming.

### 3.5 `persistence`

Event store, projections, object references, transactional outbox, migrations, and cache implementation.

### 3.6 `apps/web`

The single-image canvas, four corner cards, preview/commit state, history strip, favorites, and transport clients.

## 4. Identifiers and versioning

Use opaque identifiers for runtime identity and semantic digests for content identity.

```python
from typing import NewType

SessionId = NewType("SessionId", str)
WorldId = NewType("WorldId", str)
DesignId = NewType("DesignId", str)
RoundId = NewType("RoundId", str)
CandidateId = NewType("CandidateId", str)
ProposalId = NewType("ProposalId", str)
AssetId = NewType("AssetId", str)
```

ULIDs are suitable for sortable public IDs. They do not replace hashes.

Every persisted contract includes a schema version. Every model-dependent artifact records the model, code, scheduler, tokenizer, adapter, precision, and control-basis revisions that affect replay.

## 5. Core domain contracts

### 5.1 Model runtime

```python
from typing import Literal
from pydantic import BaseModel

class ModelRuntimeSpec(BaseModel):
    schema_version: Literal["model-runtime/v0"] = "model-runtime/v0"
    renderer_id: str
    checkpoint_uri: str
    checkpoint_digest: str
    code_revision: str
    text_encoder_revision: str
    vae_revision: str
    scheduler: str
    scheduler_revision: str
    dtype: Literal["bf16", "fp16", "fp32", "fp8", "nvfp4"]
    quantization: str | None = None
    deterministic_mode: bool = True
    license_id: str
    safety_profile: str
```

A runtime spec is immutable after a committed design references it.

### 5.2 Conditioning

```python
from pydantic import Field

class ReferenceInput(BaseModel):
    asset_id: str
    asset_digest: str
    role: Literal["subject", "style", "composition", "general"]
    weight: float = Field(ge=0.0, le=2.0)
    preprocessing_revision: str

class ConditioningState(BaseModel):
    schema_version: Literal["conditioning/v0"] = "conditioning/v0"
    prompt: str
    negative_prompt: str | None = None
    prompt_embedding_digest: str | None = None
    references: tuple[ReferenceInput, ...] = ()
    width: int
    height: int
    preservation_locks: frozenset[str] = frozenset()
    revision: str
```

Changing a load-bearing condition creates a new branch context or world transition. The renderer must never silently ignore an unsupported lock.

### 5.3 Root noise

```python
class NoiseTensorRef(BaseModel):
    schema_version: Literal["noise-tensor/v0"] = "noise-tensor/v0"
    asset_id: str
    digest: str
    shape: tuple[int, ...]
    dtype: str
    rng_algorithm: str
    rng_revision: str
    integer_seed: int | None = None

class NoiseSubspaceSpec(BaseModel):
    schema_version: Literal["noise-subspace/v0"] = "noise-subspace/v0"
    basis_asset_id: str
    basis_digest: str
    dimension: int
    construction: Literal["qr_gaussian", "learned_pca", "fixed_basis"]
    coefficient_min: float
    coefficient_max: float
    revision: str
```

The integer seed is useful provenance, but the materialized tensor or an exact verified derivation is authoritative. Adjacent integer seeds are not adjacent points in a meaningful design space.

### 5.4 Composite control action

```python
class ControlAction(BaseModel):
    schema_version: Literal["control-action/v0"] = "control-action/v0"

    noise_coefficients: tuple[float, ...] = ()
    conditioning_coefficients: tuple[float, ...] = ()
    reference_weight_deltas: tuple[float, ...] = ()
    attention_coefficients: tuple[float, ...] = ()
    adapter_coefficients: tuple[float, ...] = ()

    basis_revisions: dict[str, str]
    valid_radius: float
```

A renderer adapter may support only part of this action. Capability preflight either compiles the complete requested action or returns a typed refusal.

### 5.5 Design state

```python
class DesignState(BaseModel):
    schema_version: Literal["design-state/v0"] = "design-state/v0"

    design_id: str
    semantic_digest: str
    session_id: str
    world_id: str
    parent_design_id: str | None

    runtime: ModelRuntimeSpec
    conditioning: ConditioningState
    root_noise: NoiseTensorRef
    noise_subspace: NoiseSubspaceSpec | None

    parent_relative_action: ControlAction | None
    cumulative_action: ControlAction

    replay_level: Literal[
        "exact",
        "numerically_equivalent",
        "semantic",
        "asset_only",
    ]

    preview_asset_id: str | None = None
    final_asset_id: str | None = None
    created_at: str
```

`DesignState` is immutable. A child stores both its parent-relative proposal and its compiled cumulative action so the system can explain the branch while still replaying directly.

### 5.6 Candidate round

```python
class CandidateProposal(BaseModel):
    candidate_id: str
    proposal_id: str
    round_id: str
    slot: Literal[1, 2, 3, 4]
    parent_design_id: str

    role: Literal[
        "best_local",
        "best_diverse",
        "informative_probe",
        "controlled_surprise",
        "fallback_random",
    ]

    action: ControlAction
    proposal_probability: float | None
    expected_utility: float | None
    utility_stddev: float | None
    planner_revision: str
    preference_snapshot_id: str

    child_design_id: str | None = None
    status: Literal[
        "proposed",
        "queued",
        "preview_ready",
        "ready",
        "failed",
        "cancelled",
    ]

class CandidateRound(BaseModel):
    round_id: str
    session_id: str
    parent_design_id: str
    session_version: int
    search_radius: float
    candidates: tuple[
        CandidateProposal,
        CandidateProposal,
        CandidateProposal,
        CandidateProposal,
    ]
    created_at: str
```

## 6. Interaction events

Use a closed union of explicit events. Do not infer preference events from incidental pointer movement.

```python
class CandidateCommitted(BaseModel):
    kind: Literal["candidate_committed"]
    round_id: str
    candidate_id: str
    exposed_candidate_ids: tuple[str, ...]
    expected_session_version: int

class RoundRerolled(BaseModel):
    kind: Literal["round_rerolled"]
    round_id: str
    exposed_candidate_ids: tuple[str, ...]
    strength: Literal["soft", "explicit_dislike"] = "soft"

class DesignFavorited(BaseModel):
    kind: Literal["design_favorited"]
    design_id: str

class NewWorldRequested(BaseModel):
    kind: Literal["new_world_requested"]
    source_design_id: str
    preserve_conditions: bool = True

class HistoricalDesignRestored(BaseModel):
    kind: Literal["historical_design_restored"]
    design_id: str

class CandidatePreviewed(BaseModel):
    kind: Literal["candidate_previewed"]
    candidate_id: str
    duration_ms: int
    mechanism: Literal["hover", "press_hold", "keyboard"]
```

`CandidatePreviewed` is useful diagnostics but has zero preference weight in the first implementation.

## 7. Commands and atomic transitions

Commands include an expected session version and idempotency key.

```python
class CommitCandidateCommand(BaseModel):
    session_id: str
    round_id: str
    candidate_id: str
    expected_version: int
    idempotency_key: str

class RerollCommand(BaseModel):
    session_id: str
    round_id: str
    expected_version: int
    idempotency_key: str

class FavoriteCommand(BaseModel):
    session_id: str
    design_id: str
    favorite: bool
    idempotency_key: str

class NewWorldCommand(BaseModel):
    session_id: str
    expected_version: int
    preserve_conditions: bool
    idempotency_key: str
```

A command handler:

1. loads the current projection;
2. checks `expected_version` and command invariants;
3. produces domain events;
4. appends events and updates the projection in one transaction;
5. writes follow-up work to a transactional outbox;
6. returns the acknowledged projection.

A committed branch transition must not be able to lose its next-round generation job.

## 8. Session reducer and state machine

The reducer is pure:

```python
def reduce_session(state: SessionState, event: DomainEvent) -> SessionState:
    ...
```

Proposed server-side states:

```text
UNINITIALIZED
    └─ CreateWorld → GENERATING_ROOT

GENERATING_ROOT
    ├─ RootReady → GENERATING_ROUND
    └─ RootFailed → ERROR_RECOVERABLE

GENERATING_ROUND
    ├─ CandidateProgress → GENERATING_ROUND
    ├─ FirstCandidateReady → BROWSING
    └─ AllCandidatesFailed → ERROR_RECOVERABLE

BROWSING
    ├─ CandidateCommitted → GENERATING_ROUND
    ├─ RoundRerolled → GENERATING_ROUND
    ├─ DesignFavorited → BROWSING
    ├─ NewWorldRequested → GENERATING_ROOT
    └─ HistoricalDesignRestored → GENERATING_ROUND
```

Preview remains a client display state. It does not advance the server state machine.

## 9. HTTP and streaming API

Commands remain ordinary HTTP for idempotency and debugging. Use Server-Sent Events first for progress streaming; WebSockets can be added if bidirectional real-time needs appear.

```text
POST /v1/worlds
GET  /v1/sessions/{session_id}
GET  /v1/sessions/{session_id}/stream
POST /v1/rounds/{round_id}/commit
POST /v1/rounds/{round_id}/reroll
POST /v1/designs/{design_id}/favorite
DELETE /v1/designs/{design_id}/favorite
POST /v1/sessions/{session_id}/new-world
POST /v1/sessions/{session_id}/restore
POST /v1/designs/{design_id}/export
```

Example world request:

```json
{
  "renderer_profile": "flux2-klein-4b-local/v0",
  "prompt": "an impossible coastal pavilion",
  "references": [],
  "width": 1024,
  "height": 1024,
  "noise_subspace_dimension": 16
}
```

Stream events:

```text
session.updated
round.created
candidate.queued
candidate.preview_ready
candidate.final_ready
candidate.failed
round.invalidated
optimizer.updated
```

Every event carries a monotonic stream sequence, session version, and relevant round identifier. The browser ignores stale round progress.

## 10. Renderer interface

```python
from collections.abc import AsyncIterator
from typing import Protocol

class RendererAdapter(Protocol):
    def capabilities(self) -> "RendererCapabilities": ...

    async def preflight(
        self,
        parent: DesignState | None,
        action: ControlAction,
        output: "OutputProfile",
    ) -> "AcceptedRenderPlan | RenderRefusal": ...

    async def materialize_root(
        self,
        request: "CreateWorldRequest",
    ) -> DesignState: ...

    async def render(
        self,
        plan: "AcceptedRenderPlan",
    ) -> AsyncIterator["RenderProgress"]: ...
```

A refusal is data:

```python
class RenderRefusal(BaseModel):
    code: Literal[
        "unsupported_control_space",
        "incompatible_parent",
        "license_restriction",
        "safety_refusal",
        "resource_limit",
        "nondeterministic_configuration",
    ]
    message: str
    unsupported_fields: tuple[str, ...] = ()
```

The adapter must never silently drop unsupported control components.

## 11. Searchable initial-noise subspace

For root noise $z_0 \in \mathbb{R}^N$, construct an orthonormal basis:

$$
B \in \mathbb{R}^{N \times d}, \qquad B^T B = I.
$$

Project the root into that subspace:

$$
u_0 = B^T z_0, \qquad z_\perp = z_0 - Bu_0.
$$

Search the low-dimensional coefficients:

$$
z(u) = z_\perp + Bu.
$$

This keeps all components orthogonal to the subspace fixed. The coefficients are continuous and bounded; the integer seed is not optimized.

```python
import torch

@torch.no_grad()
def make_noise_subspace(
    z0: torch.Tensor,
    dimension: int,
    generator: torch.Generator,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    flat = z0.detach().float().reshape(-1)
    n = flat.numel()
    if not 0 < dimension < n:
        raise ValueError("dimension must be between 1 and N-1")

    random_matrix = torch.randn(
        n,
        dimension,
        generator=generator,
        device=flat.device,
        dtype=flat.dtype,
    )
    basis, _ = torch.linalg.qr(random_matrix, mode="reduced")
    root_coefficients = basis.T @ flat
    fixed_residual = flat - basis @ root_coefficients
    return basis, fixed_residual, root_coefficients

@torch.no_grad()
def apply_noise_coefficients(
    basis: torch.Tensor,
    fixed_residual: torch.Tensor,
    coefficients: torch.Tensor,
    original_shape: tuple[int, ...],
    output_dtype: torch.dtype,
) -> torch.Tensor:
    flat = fixed_residual + basis @ coefficients
    return flat.reshape(original_shape).to(dtype=output_dtype)
```

Store the basis, residual, root coefficients, dtype, and digests—or an exact deterministic derivation with replay verification. Do not assume a noise direction transfers to another world.

## 12. Preference learning interface

```python
class PreferenceModel(Protocol):
    @property
    def snapshot_id(self) -> str: ...

    def update(self, observations: list["ChoiceObservation"]) -> None: ...

    def predict(self, actions: torch.Tensor) -> "UtilityPosterior": ...

    def sample_functions(
        self,
        actions: torch.Tensor,
        count: int,
        generator: torch.Generator,
    ) -> torch.Tensor: ...
```

A four-way observation includes an outside option:

```python
class ChoiceObservation(BaseModel):
    round_id: str
    action_vectors: list[list[float]]
    chosen_index: int | None  # None means reroll / none of these
    weight: float
    exposure_mask: list[bool]
    proposal_probabilities: list[float | None]
    occurred_at: str
```

Only rendered and meaningfully exposed candidates enter the observation.

Implement two backends behind the same interface:

1. a Bayesian linear discrete-choice model for speed and robustness;
2. a pairwise or multi-choice GP approximation for low-data research comparisons.

BoTorch and GPyTorch objects must not leak into domain or API contracts.

## 13. Persistent preference prior

Start with several weighted interest modes rather than one averaged embedding:

```python
class PersistentInterest(BaseModel):
    interest_id: str
    centroid: list[float]
    covariance_diagonal: list[float]
    weight: float
    evidence_count: int
```

Stars and exports have strong persistent weight. Commits have only small persistent weight because a selected design may merely be a promising route. Reroll and new-world reset do not automatically update the persistent prior.

The interface should later admit a sequence-conditioned model inspired by Preference Prior without changing session semantics.

## 14. Candidate planner

```python
class CandidatePlanner(Protocol):
    def propose_round(
        self,
        *,
        parent: DesignState,
        preference: PreferenceModel,
        persistent_prior: "PersistentPreference",
        capability: "RendererCapabilities",
        search_state: "BranchSearchState",
        generator: torch.Generator,
    ) -> CandidateRound: ...
```

Build a hidden pool larger than four using:

- local trust-region perturbations;
- posterior Thompson samples;
- UCB or expected-improvement candidates;
- one proposal from each active persistent interest mode;
- bounded random calibration candidates;
- optional correlated-noise perturbations.

Select four candidates with distinct roles:

```python
def choose_four(pool, posterior, predicted_features):
    chosen = []
    chosen.append(argmax_expected_utility(pool))
    chosen.append(argmax_utility_with_diversity(pool, chosen, predicted_features))
    chosen.append(argmax_uncertainty(pool, chosen, predicted_features))
    chosen.append(argmax_controlled_surprise(pool, chosen, predicted_features))
    return chosen
```

The proposal record stores the policy role, scores, uncertainty, preference snapshot, and proposal probability or enough information to reconstruct it.

### 14.1 Branch search state

```python
class BranchSearchState(BaseModel):
    trust_center: list[float]
    radius: float
    consecutive_rerolls: int
    consecutive_commits: int
    exploration_beta: float
    revision: str
```

A soft reroll increases radius or exploration modestly. A commit moves the trust center. Repeated local successes may shrink the radius.

## 15. Feature extraction

Use a versioned feature bundle rather than one CLIP vector:

```python
class ImageFeatureBundle(BaseModel):
    semantic: list[float]
    style: list[float]
    composition: list[float]
    perceptual: list[float]
    quality_scores: dict[str, float]
    artifact_scores: dict[str, float]
    encoder_revisions: dict[str, str]
```

Potential encoders include CLIP/SigLIP-like semantic features and DINO-like visual features, but exact choices require experiments. Cache by asset digest plus preprocessing and encoder revisions.

## 16. Frontend state

Use an explicit reducer. Preview and commitment must never share one mutable field.

```ts
type UiState = {
  sessionId: string;
  sessionVersion: number;
  committed: DesignView;
  preview: DesignView | null;
  activeRound: CandidateRoundView | null;
  lastTen: DesignView[];
  favorites: Set<string>;
  historyOpen: boolean;
  connection: "online" | "reconnecting" | "offline";
};

type UiAction =
  | { type: "previewStarted"; candidateId: string }
  | { type: "previewEnded"; candidateId: string }
  | { type: "commitRequested"; candidateId: string }
  | { type: "sessionProjectionReceived"; projection: SessionProjection }
  | { type: "candidateProgressReceived"; event: CandidateProgress }
  | { type: "roundInvalidated"; roundId: string }
  | { type: "historyToggled" };
```

The reducer must handle fast pointer movement correctly: an old `previewEnded` event cannot clear a newer preview. Candidate progress for stale rounds is ignored.

Suggested component tree:

```text
ArtOptimizerPage
├── ConditionsDrawer
├── DesignCanvas
│   ├── CurrentDesignLayer
│   └── PreviewDesignLayer
├── CandidateCorners
│   └── CandidateCard × 4
├── CommandBar
└── HistoryDrawer
```

## 17. Persistence model

Suggested relational tables:

```text
users
sessions
worlds
design_states
design_edges
candidate_rounds
candidate_proposals
interaction_events
session_projections
favorites
model_runtime_specs
preference_snapshots
branch_search_snapshots
generation_jobs
assets
feature_bundles
outbox
```

Large images, noise tensors, bases, references, and optional intermediate latents live in object storage. The database stores digests, locations, sizes, and lifecycle status.

The event log retains original interaction facts. Preference observations and read models are rebuildable projections.

## 18. Semantic hashing and replay

Canonical JSON hashing rules:

- stable field order;
- explicit schema versions;
- timestamps excluded from semantic identity;
- storage URLs excluded from content identity;
- tensor bytes hashed with shape and dtype;
- every load-bearing model and basis revision included;
- no implicit default that can change between software versions.

```python
def design_state_digest(state: DesignState) -> str:
    payload = state.model_dump(
        exclude={
            "design_id",
            "created_at",
            "preview_asset_id",
            "final_asset_id",
        },
        mode="json",
    )
    return sha256(canonical_json(payload)).hexdigest()
```

A design-state digest is not an image digest. Preview and final render bytes have separate asset digests.

Replay tests should classify results as:

- exact;
- numerically equivalent within a recorded tolerance;
- semantically replayable but nondeterministic;
- asset-only because the runtime is unavailable.

## 19. Generation jobs

Priority classes:

```text
P0 committed-root render
P1 visible candidate preview
P2 visible candidate finalization
P3 selected-candidate speculative children
P4 likely-candidate speculative children
P5 features, research, and backfill
```

A render request key is a semantic digest. Identical requests share work. Cancellation is cooperative: stale work may finish, but it cannot mutate the active round.

Every job carries:

```text
session_id
session_version
world_id
parent_design_id
round_id
candidate_id
proposal_id
render_request_digest
```

## 20. Tests

### 20.1 Domain properties

- preview never changes committed state;
- commit creates exactly one branch edge;
- reroll preserves committed state and root noise;
- new world creates independent root noise without negative evidence;
- history restore preserves prior descendants and creates a fork on the next commit;
- repeated commands with the same idempotency key are harmless;
- stale versions and stale rounds are rejected;
- the last-ten projection is correct.

### 20.2 Renderer tests

- replay after process restart;
- digest changes when any load-bearing revision changes;
- unsupported actions return typed refusals;
- preview and final assets refer to the same design state;
- batching does not cross-contaminate noise or conditioning;
- exact or bounded replay matches the declared level.

### 20.3 Optimizer tests

Use simulated utilities to test:

- convergence under stable preferences;
- recovery after preference drift;
- outside-option/reroll behavior;
- diversity of four-item slates;
- absence of duplicate actions;
- reproducibility under a fixed optimizer RNG;
- comparison with random, top-four-mean, and single-dimension baselines.

### 20.4 Browser tests

Playwright scenarios:

- hover previews and restores;
- click commits the hovered corner;
- fast movement between corners cannot restore the wrong image;
- touch hold previews while tap commits;
- keyboard controls match pointer behavior;
- stale stream events are ignored;
- reroll keeps the current design;
- new world remains recoverable through history;
- failed candidates are excluded from preference evidence;
- reduced-motion mode works.

### 20.5 Fake renderer

Ordinary CI must not require a GPU. A deterministic fake renderer can map state digests to generated gradients or geometric patterns, supporting complete API and UI tests.

## 21. Performance receipts

Performance claims must record:

- GPU and driver;
- model/checkpoint digest;
- dtype and quantization;
- resolution and batch size;
- inference steps and scheduler;
- warm or cold state;
- preview and final profile;
- software revision.

Initial target budgets are hypotheses:

```text
command acknowledgement             < 150 ms typical
preference update                   < 100 ms for the MVP model
proposal construction               < 100 ms excluding rendering
first candidate preview             < 1.5 s on target GPU
all four previews                   < 3.0 s on target GPU
hover visual swap                   < 50 ms after asset load
```

Vendor benchmark numbers are not project benchmarks until reproduced.

## 22. CI gates

```text
Python formatting, linting, and type checks
TypeScript formatting, linting, and type checks
JSON Schema generation drift check
unit and property tests
domain fixture conformance
frontend component tests
Playwright with fake renderer
migration test
license manifest check
secret scan
```

GPU integration tests can run on a scheduled or self-hosted runner.

## 23. Implementation milestones

### Milestone 0 — Contracts and fake renderer

- monorepo tooling;
- versioned contracts;
- pure session reducer;
- SQLite event repository;
- fake deterministic renderer;
- complete one-canvas/four-corner UI;
- commit, reroll, favorite, new-world, and last-ten flows;
- end-to-end browser tests.

### Milestone 1 — Real renderer

- FLUX.2 [klein] 4B adapter;
- materialized root-noise persistence;
- four-candidate batching or streaming;
- replay manifest and verification;
- local asset cache;
- measured latency receipt.

### Milestone 2 — Preference optimizer

- Bayesian linear discrete-choice model;
- four-role slate policy;
- reroll outside option;
- simulated-user benchmark;
- proposal and exposure telemetry.

### Milestone 3 — Hybrid control space

- searchable initial-noise subspace;
- one conditioning or reference control family;
- renderer capability preflight;
- branch trust region;
- direction-sweep and transfer tests.

### Milestone 4 — Persistent preference

- favorites and exports as durable evidence;
- multi-interest centroid prior;
- new-world cold-start experiment;
- preference export and deletion controls.

### Milestone 5 — Research extensions

- PairwiseGP and MultiBO-style alternatives;
- attention and adapter controls;
- Krea 2 and SANA-Sprint renderer benchmarks;
- offline LoRA or DPO consolidation;
- calibrated direction quantities and branch-map UI.

## 24. Scope of the first code pull request

The first code pull request should not begin with the real image model. It should establish:

- repository tooling;
- versioned domain contracts;
- the pure session reducer;
- SQLite-backed events and projections;
- the deterministic fake renderer;
- the single-image/four-corner interface;
- exact semantics for commit, reroll, favorite, new world, and restore;
- end-to-end tests proving those distinctions.

That gives the renderer and optimizer a stable product skeleton instead of burying the UI semantics under GPU integration work.
