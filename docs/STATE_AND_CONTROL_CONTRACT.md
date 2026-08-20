# State and Control Contract

**Status:** Normative v0 domain contract  
**Last updated:** 2026-08-20

This document separates four concepts that must not be collapsed:

1. immutable generative state;
2. branch/navigation state;
3. world-level control coordinates;
4. preference-model snapshots.

It also constrains how persistent preference components may affect candidates without introducing hidden per-candidate conditions.

Where this document conflicts with earlier examples, this document governs v0.

## 1. Core rule

> A `DesignState` says how to render an image. A `BranchNode` says where that design sits in one user's interaction and learning history.

The same generative design may be favorited without being committed, exported without becoming a branch node, or revisited through a branch checkpoint with a particular local posterior. Preference/search metadata therefore does not belong inside the immutable generative state.

## 2. World

A world fixes every load-bearing basis needed to interpret absolute action coordinates.

```python
class World(BaseModel):
    world_id: str
    session_id: str

    runtime_manifest_id: str
    conditioning_manifest_id: str
    control_basis_manifest_id: str
    root_noise_artifact_id: str

    root_design_id: str
    root_branch_node_id: str

    created_from_atlas_snapshot_id: str | None
    world_preference_context_id: str | None
    created_at: str
```

Within one world, these are immutable:

- model/runtime;
- prompt and structural conditions;
- reference identities;
- root-noise tensor;
- coordinate meanings and bounds;
- selected atlas reference slots;
- aspect ratio and design-space output constraints.

Changing any of them creates a new world.

## 3. Control basis

The action vector is meaningful only through a versioned `ControlBasisManifest`.

```python
class ControlCoordinate(BaseModel):
    coordinate_id: str
    index: int
    kind: Literal[
        "conditioning_direction",
        "reference_weight",
        "adapter_weight",
        "attention_direction",
        "noise_tangent",
    ]

    lower: float
    upper: float
    distance_scale: float
    default: float

    compiler_payload_digest: str
    scope: Literal["world"] = "world"
    calibration_receipt_id: str | None

class AtlasReferenceSlot(BaseModel):
    slot_id: str
    component_id: str
    exemplar_design_id: str
    reference_asset_id: str
    role: Literal["style", "composition", "general"]
    coordinate_id: str

class ControlBasisManifest(BaseModel):
    manifest_id: str
    schema_version: Literal["control-basis/v0"]
    renderer_profile_id: str
    coordinates: tuple[ControlCoordinate, ...]
    atlas_reference_slots: tuple[AtlasReferenceSlot, ...]
    digest: str
```

The manifest contains at most sixteen coordinates in v0.

Every coordinate has one stable interpretation for the entire world. The renderer compiles an absolute vector with no hidden mutation of prompt, reference identity, adapter identity, or basis.

## 4. Persistent atlas references are fixed at world creation

Persistent preference may select up to two components/exemplars when constructing a world. If the renderer supports bounded reference guidance, those exemplars become fixed reference slots in the world control basis.

Example:

```text
coordinate 0..7      model/conditioning directions
coordinate 8         weight of atlas component A exemplar
coordinate 9         weight of atlas component B exemplar
coordinate 10..13    adapter or attention directions
coordinate 14..15    optional noise tangent directions
```

Candidates may vary the **weights** of these fixed slots because those weights are declared action coordinates.

Candidates may not silently swap the exemplar identity, add a new reference, or use a different hidden prompt. Doing so would place candidates in different design spaces and invalidate the local action model.

If an atlas component is relevant but was not installed in the world basis, v0 choices are:

1. start a new world whose basis includes it;
2. use it only in an oversample-and-rerank experiment where all rendered candidates still have declared states;
3. fall back to the controlled-surprise role.

No candidate-specific hidden guidance is allowed.

## 5. Design state

`DesignState` is immutable generative provenance.

```python
class DesignState(BaseModel):
    design_id: str
    schema_version: Literal["design-state/v0"]
    semantic_digest: str

    world_id: str
    parent_design_id: str | None
    created_from_candidate_id: str | None

    absolute_action: tuple[float, ...]
    parent_delta: tuple[float, ...] | None

    runtime_manifest_id: str
    conditioning_manifest_id: str
    control_basis_manifest_id: str
    root_noise_artifact_id: str

    replay_level: Literal[
        "byte_exact",
        "pixel_equivalent",
        "semantic",
        "asset_only",
    ]

    preview_asset_id: str | None
    final_asset_id: str | None
    render_manifest_id: str
    created_at: str
```

It does **not** contain:

- current-session pointer state;
- local preference posterior;
- trust-region radius;
- atlas activation weights;
- favorite status;
- history position;
- exposure facts.

Those belong to interaction projections.

## 6. Candidate proposal

A candidate is a proposed immutable design state attached to one round.

```python
class CandidateProposal(BaseModel):
    candidate_id: str
    round_id: str
    slot: Literal[1, 2, 3, 4]
    role: str

    parent_design_id: str
    proposed_absolute_action: tuple[float, ...]
    proposed_parent_delta: tuple[float, ...]

    resulting_design_id: str | None
    renderer_plan_id: str

    local_preference_snapshot_id: str
    world_preference_context_id: str | None
    atlas_component_ids: tuple[str, ...]
    atlas_reference_slot_ids: tuple[str, ...]

    planner_revision: str
    planner_rng_state_digest: str
    proposal_probability_or_density: float | None
    role_fallback_reason: str | None
```

The atlas IDs are explanatory provenance for coordinates already declared in the world basis; they are not hidden conditions.

## 7. Branch node

A `BranchNode` binds a committed generative design to one navigation and learning checkpoint.

```python
class BranchNode(BaseModel):
    branch_node_id: str
    session_id: str
    world_id: str
    design_id: str

    parent_branch_node_id: str | None
    commit_event_id: str | None

    inherited_local_preference_snapshot_id: str
    active_local_preference_snapshot_id: str
    branch_search_snapshot_id: str
    world_preference_context_id: str | None

    created_at: str
```

The root design has a root branch node with no commit event.

A candidate design can exist without a branch node. It receives one only when committed. Favoriting an uncommitted candidate stores the design but does not fabricate navigation history.

## 8. Local learner update timing

A commit must not mutate the already-created `DesignState`.

The sequence is:

1. candidate design state exists and is durable;
2. `CandidateCommitted` creates a new branch node using the inherited/previous local snapshot;
3. one typed choice observation is queued;
4. learner publishes an immutable updated snapshot;
5. `LocalPreferenceSnapshotAttached` updates the branch-node projection's active snapshot;
6. rounds proposed afterward record whichever active snapshot was available.

The underlying event history remains append-only. If the learner update fails, the branch node keeps the inherited snapshot and interaction continues.

## 9. Branch search snapshot

Trust-region and exploration state are also separate from `DesignState`.

```python
class BranchSearchSnapshot(BaseModel):
    snapshot_id: str
    branch_node_id: str
    center_absolute_action: tuple[float, ...]
    radius: float
    consecutive_commits: int
    consecutive_rerolls: int
    exploration_beta: float
    policy_revision: str
```

Restoring history restores a branch node, which restores both the local-preference and search snapshots associated with that point.

## 10. History and favorites use different identities

- **History:** ordered `BranchNode` IDs.
- **Favorite:** `DesignState` ID plus favorite evidence event.

This is why a user can favorite candidate A, commit candidate B, and later branch from either without conflating persistent taste with branch navigation.

## 11. Session projection

```python
class SessionProjection(BaseModel):
    session_id: str
    version: int

    active_world_id: str
    current_branch_node_id: str
    current_design_id: str
    active_round_id: str | None

    last_ten_branch_node_ids: tuple[str, ...]
    favorite_design_ids: frozenset[str]
```

The committed design is derived from the current branch node. Preview remains client-local.

## 12. World creation from the preference atlas

World creation performs these steps:

1. load a persistent-atlas snapshot;
2. compute context responsibilities from prompt, references, and optional prior anchor;
3. select zero, one, or two atlas components under the world-creation policy;
4. choose fixed exemplars for supported reference slots;
5. create the immutable control-basis manifest;
6. materialize root noise;
7. create neutral root action and root `DesignState`;
8. create root `BranchNode` with fresh local/search snapshots;
9. propose the first quartet by varying declared coordinates.

The selection probabilities and outside-prior decision are recorded.

## 13. Absolute render contract

```python
class RendererAdapter(Protocol):
    async def compile_world(
        self,
        runtime: ModelRuntimeSpec,
        conditions: ConditioningState,
        atlas_slots: tuple[AtlasReferenceSlotRequest, ...],
        root_noise: NoiseTensorRef,
    ) -> ControlBasisManifest | RenderRefusal: ...

    async def compile_action(
        self,
        world: World,
        absolute_action: tuple[float, ...],
    ) -> AcceptedRenderPlan | RenderRefusal: ...
```

`compile_action` must be a pure function of the immutable world manifests and the supplied absolute vector, modulo recorded runtime nondeterminism. It cannot inspect user history and quietly alter the render.

## 14. Semantic identities

Use separate digests:

```text
world digest
control-basis digest
design-state digest
render-request digest
render-result digest
branch-node identity
local-preference snapshot digest
search snapshot digest
atlas snapshot digest
```

A branch node is not content-addressed solely by the design state because learning/navigation metadata differs from generative identity.

## 15. Concurrency

Commit transaction:

1. validate session version, round, and candidate;
2. append `CandidateCommitted`;
3. create branch node;
4. close round;
5. advance current branch pointer;
6. enqueue learner and next-round work through the transactional outbox.

Only one command may advance a given session version.

A late learner snapshot can attach to its intended branch node but cannot mutate a newer round's recorded proposal snapshot.

## 16. Required tests

1. favoriting an uncommitted candidate creates no branch node;
2. committing it later creates exactly one branch node;
3. learner updates never mutate a design-state digest;
4. restoring history restores branch-local and search snapshots;
5. the same design state cannot acquire hidden new reference identities;
6. every candidate's atlas guidance maps to fixed world coordinates;
7. changing an atlas exemplar creates a new control-basis manifest/world;
8. absolute action replay is independent of current session pointer;
9. sibling branch nodes may reference different learner snapshots while retaining immutable design states;
10. candidate generation cannot read unrecorded user history inside the renderer;
11. concurrent commits create at most one child branch node from the active version;
12. world, design, branch, and model digests change only for their declared load-bearing fields.

## 17. Consequence for the earlier documents

Interpret earlier statements such as “a design stores the local posterior” as shorthand for:

> the committed branch checkpoint associated with that design stores the local posterior.

Interpret “compile a persistent exemplar proposal” as:

> vary a fixed atlas reference coordinate installed in the world's control basis, or start a new world.

These clarifications preserve the intended product while keeping the statistical model honest.
