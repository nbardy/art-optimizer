# Architecture

**Status:** Proposed architecture for the first executable vertical slice  
**Last updated:** 2026-08-19

## 1. Architectural objective

Art Optimizer must support an interaction that feels immediate and simple while preserving enough information to make every design choice reproducible, learnable, and forkable.

The visible product is:

```text
one committed design
+ four previewable candidates
+ select / reroll / star / new world / history
```

The underlying system is:

```text
replayable generative state
+ event-sourced interaction history
+ branch-local preference posterior
+ persistent multi-interest prior
+ uncertainty-aware candidate planner
+ replaceable GPU renderer
```

The initial architecture should be a **modular monolith with separate GPU workers**, not a premature fleet of microservices. Logical boundaries are explicit from day one so components can later be scaled independently.

## 2. Goals

The architecture must:

1. preserve the distinction between preview and commit;
2. replay a committed design exactly when the configured renderer supports exact replay;
3. retain a complete immutable branch tree while showing only the last ten designs in the MVP UI;
4. stream four candidate slots independently;
5. prevent stale render results from replacing a newer round;
6. separate persistent preference from branch-local intent;
7. support reroll as an outside option and new world as a non-negative reset;
8. keep model-specific controls behind a renderer capability contract;
9. record proposal policy and exposure data for later off-policy evaluation;
10. run locally for researchers and scale to hosted GPU workers without changing product semantics.

## 3. Non-goals for the first version

The first architecture does not require:

- real-time multi-user collaboration;
- a public social feed;
- per-click model fine-tuning;
- a fully distributed online feature store;
- long-horizon reinforcement learning;
- a universal ontology for every image model;
- a visual graph editor for control manifolds;
- guaranteed replay after a required third-party model revision disappears.

## 4. System context

```text
┌──────────────────────────────┐
│ Web client                   │
│ canvas, corners, history     │
└──────────────┬───────────────┘
               │ HTTPS + SSE/WebSocket
┌──────────────▼───────────────┐
│ Application control plane    │
│ commands, state, auth, API   │
├──────────────────────────────┤
│ Session coordinator          │
│ branch and round state       │
├──────────────────────────────┤
│ Candidate planner            │
│ preference + acquisition     │
├──────────────────────────────┤
│ Preference learner           │
│ local posterior + prior      │
└──────────┬───────────┬───────┘
           │           │
     jobs  │           │ events/features
┌──────────▼──────┐  ┌─▼────────────────┐
│ GPU render pool │  │ Persistence      │
│ model adapters  │  │ DB/object/cache  │
└──────────┬──────┘  └──────────────────┘
           │ images/features
           └─────────────────────────────► control plane
```

## 5. Logical components

### 5.1 Web client

Responsibilities:

- render the committed design and four corner candidates;
- maintain temporary preview state locally;
- send explicit commands for commit, reroll, star, new world, restore, and export;
- subscribe to independent candidate-slot updates;
- ignore events for stale round IDs;
- expose touch, keyboard, accessibility, and reduced-motion interactions;
- upload prompt/reference assets through signed endpoints;
- retain no authoritative branch mutation that has not been acknowledged by the server.

The client may optimistically animate a commit, but the server-issued state version remains authoritative.

### 5.2 Application control plane

Responsibilities:

- authentication and authorization;
- command validation and idempotency;
- API and streaming connections;
- transactionally appending domain events;
- deriving current session state;
- issuing candidate-generation workflows;
- coordinating object storage and signed URLs;
- enforcing configured model and content-policy constraints.

A Python service is appropriate because the optimizer and renderer ecosystem is Python-heavy. The web client remains TypeScript.

### 5.3 Session coordinator

The coordinator owns the state machine for one interactive session:

```text
NO_WORLD
  └─ create world → ROUND_PLANNING
ROUND_PLANNING
  └─ proposals accepted → ROUND_RENDERING
ROUND_RENDERING
  ├─ slot results stream → ROUND_READY_PARTIAL
  ├─ four ready → ROUND_READY
  ├─ commit → ROUND_PLANNING on child state
  ├─ reroll → ROUND_PLANNING on same state
  ├─ new world → ROUND_PLANNING on new root
  └─ restore → ROUND_PLANNING on restored state
```

Preview never enters this server state machine because it is not a domain mutation.

### 5.4 Candidate planner

Responsibilities:

- build a candidate action pool from the current state;
- obtain persistent and branch-local preference predictions;
- allocate the four proposal roles;
- enforce action bounds and preservation locks;
- select a diverse slate;
- record proposal policy, scores, uncertainty, and a probability or reconstructable sampling distribution;
- decide which descendants should be speculatively rendered.

The planner is deterministic given a planner seed, model snapshots, and inputs. Exploration randomness is recorded.

### 5.5 Preference learner

The preference subsystem contains two models:

1. **Persistent prior** — multi-session and eventually collaborative preference modes derived mostly from stars, exports, revisits, and explicit negative actions.
2. **Branch-local posterior** — a fast model updated from four-way selections and rerolls within the current world/branch.

The first implementation can use:

- a Bayesian linear discrete-choice model over image/action features; or
- a pairwise/preferential GP for small bounded action spaces.

Model updates produce immutable snapshots. Every round records the exact preference snapshot used to propose it.

### 5.6 GPU renderer

The renderer consumes a model-independent render request and one model-specific adapter. It:

- materializes or retrieves the root-noise tensor;
- applies conditioning, references, adapters, and bounded control actions;
- renders preview and final assets;
- emits progress and result manifests;
- calculates or delegates image features;
- records hardware, precision, model digest, sampler, steps, and software revisions;
- refuses unsupported controls instead of silently ignoring them.

### 5.7 Feature service

Initially this can run inside GPU workers or the control plane. It computes versioned representations used for:

- semantic similarity;
- style and composition comparison;
- quality and artifact detection;
- duplicate suppression;
- persistent preference updates;
- slate diversity.

Feature vectors are never treated as timeless. Each has an encoder ID and digest.

### 5.8 Persistence

The logical stores are:

- **relational database:** users, sessions, worlds, design states, rounds, candidates, events, model snapshots, jobs, and manifests;
- **object storage:** rendered images, reference images, materialized noise tensors, adapter files, and optional feature arrays;
- **queue/cache:** generation jobs, distributed locks, hot session projections, speculative results, and rate limits.

For local development these can collapse to SQLite, a filesystem object directory, and an in-process queue. Hosted deployment can use PostgreSQL, S3-compatible storage, and Redis or a durable job broker.

## 6. Core domain artifacts

### 6.1 DesignState

A `DesignState` is the authoritative, immutable node in the branch tree:

```text
design_state_id
parent_design_state_id
world_id
model_manifest_id
root_noise_artifact_id
conditioning_manifest_id
reference_manifest_id
cumulative_control_action
output_constraints
render_asset_ids
created_from_candidate_id
semantic_digest
created_at
```

The PNG/JPEG is an output. The state and its provenance are authoritative.

### 6.2 World

A world defines one stochastic root and branch-local optimization context:

```text
world_id
session_id
root_design_state_id
root_noise_artifact_id
base_conditions
local_preference_snapshot_id
created_at
closed_at
```

`New world` creates another world while preserving account-level preference.

### 6.3 CandidateRound

```text
round_id
world_id
parent_design_state_id
branch_version
planner_revision
planner_seed
persistent_prior_snapshot_id
local_posterior_snapshot_id
status
created_at
```

Exactly four candidate slots are requested for the MVP, although a slot can fail independently.

### 6.4 CandidateProposal

```text
candidate_id
round_id
slot
role
control_action
proposal_policy
proposal_probability_or_density
predicted_mean
predicted_uncertainty
diversity_metadata
render_job_id
resulting_design_state_id
exposure_state
```

### 6.5 InteractionEvent

Important events include:

```text
WorldCreated
CandidateRoundProposed
CandidatePreviewReady
CandidateFinalReady
CandidateFailed
CandidateCommitted
RoundRerolled
DesignStarred
DesignUnstarred
HistoryStateRestored
WorldReset
DesignExported
DesignHidden
```

Hover/hold can be logged as product telemetry but is not a domain preference event in the MVP.

### 6.6 ModelManifest

```text
model_family
checkpoint_uri
checkpoint_digest
license_id
adapter_digests
runtime_revision
precision
sampler
steps
guidance
scheduler
vae_or_decoder_digest
capability_profile_id
```

### 6.7 RenderManifest

```text
render_request_digest
model_manifest_id
hardware_class
software_image_digest
input_state_digest
action_digest
preview_asset_id
final_asset_id
started_at
completed_at
replay_level
warnings
```

## 7. Command and data flows

### 7.1 Start a session

1. Client submits prompt, optional references, model profile, aspect ratio, and output constraints.
2. Control plane validates licenses, capabilities, and policy.
3. Coordinator creates a session and world.
4. Renderer materializes a root-noise tensor and root design state.
5. Preference learner supplies a persistent prior snapshot.
6. Planner proposes the first quartet.
7. Slots stream independently to the client.

### 7.2 Preview a candidate

Preview is entirely client-local:

```text
pointer enter / press-hold
→ preview candidate asset on main canvas
→ no domain command
→ pointer leave / release
→ restore committed asset
```

Optional telemetry is sampled and clearly separated from preference evidence.

### 7.3 Commit a candidate

1. Client sends `CommitCandidate(round_id, candidate_id, expected_branch_version, idempotency_key)`.
2. Server verifies that the candidate belongs to the active round and is selectable.
3. In one transaction it appends `CandidateCommitted`, advances the branch version, and marks the round closed.
4. The selected candidate’s resulting `DesignState` becomes current.
5. One four-way choice observation is queued for the local learner.
6. Stale jobs are cancelled or demoted.
7. A new round is planned from the child state.

### 7.4 Reroll

1. Client sends `RerollRound` for the active round.
2. Server appends one outside-option event.
3. Current `DesignState`, world, and root noise remain unchanged.
4. Local exploration radius or uncertainty weight may increase.
5. A replacement quartet is proposed with a new round ID.

### 7.5 Star

`StarDesign` is independent of navigation. It stores a durable favorite and queues a stronger persistent-preference update. A candidate may be starred without becoming current if its full state is already materialized.

### 7.6 New world

1. Preserve the current state in history automatically.
2. Append `WorldReset` with a reason such as explicit user action.
3. Draw and store a new root-noise tensor.
4. Retain prompt/references/settings unless changed.
5. initialize a new branch-local posterior from the persistent prior.
6. Propose the first quartet in the new world.

No negative label is applied to the previous world.

### 7.7 Restore history

Restoring a prior state changes the current branch pointer to that immutable node. The next commit creates another child, preserving the original descendants.

## 8. Event sourcing and projections

Interaction events are append-only. Current state is a projection over those events plus immutable render artifacts.

Benefits:

- auditability of preference labels;
- exact reconstruction of branch decisions;
- the ability to change event weighting and retrain models;
- clean separation between user action and current algorithm interpretation;
- support for undo/fork without destructive updates;
- offline policy evaluation.

Not every telemetry event needs the same durable retention period. Domain events and proposal/exposure records are durable; high-frequency pointer telemetry may be sampled or discarded.

## 9. Determinism and replay

### 9.1 Reproducibility levels

Each render declares one of:

- **byte-exact:** identical output bytes on the supported runtime;
- **pixel-equivalent:** numerically equivalent pixels within a specified tolerance;
- **semantic replay:** same inputs and model state, but backend nondeterminism may alter pixels;
- **asset-only:** original rendered asset retained, rerender unavailable.

The UI must not imply byte-exact replay when only the stored output asset is available.

### 9.2 What must be stored

At minimum:

- checkpoint and adapter digests;
- materialized initial noise or its exact generated artifact;
- prompt/tokenization and reference inputs;
- cumulative control action;
- scheduler/sampler/steps/guidance;
- precision and runtime revisions;
- output dimensions;
- random generators and recorded seeds for every stochastic operation.

### 9.3 Content-addressed identity

Use layered digests:

```text
source asset digest
normalized conditioning digest
root-noise digest
control-action digest
render-request digest
render-result digest
feature digest
preference-snapshot digest
planner snapshot digest
```

A `DesignState` ID should not be derived solely from its PNG because two different states can render similar images and one state may have several output resolutions.

## 10. Renderer capability contract

The product requests capabilities rather than assuming model internals.

```text
RendererCapabilities
  text_to_image
  image_to_image
  multi_reference
  deterministic_noise_injection
  prompt_embedding_controls
  attention_controls
  adapter_mixing
  preview_then_finalize
  batch_generation
  supported_resolutions
  replay_level
  license_constraints
```

The adapter returns either:

```text
AcceptedPlan
```

or:

```text
Refusal(reason, unsupported_requirements, alternatives)
```

Silently dropping an unsupported preservation lock or control direction is prohibited.

## 11. Concurrency and stale work

Every mutable command includes:

- session ID;
- active world ID;
- expected branch version;
- active round ID where applicable;
- idempotency key.

Every render job includes:

- parent design ID;
- branch version;
- round ID;
- candidate ID and slot;
- proposal ID;
- render-request digest.

The client and server ignore stale visible results. Completed stale renders may remain in a bounded cache if they are reusable, but cannot mutate the active projection.

Only one command may advance a branch version. Duplicate commits with the same idempotency key return the original result.

## 12. Scheduling and latency

### 12.1 Priority classes

1. active-round preview render;
2. active-round finalization;
3. likely-child speculative render;
4. deterministic replay/export;
5. feature extraction and offline model updates;
6. low-probability speculative work.

### 12.2 Batching

The four slots should be batched when the renderer supports it, but completion remains independently streamable. The scheduler can combine compatible jobs from different sessions without changing their recorded noise or action state.

### 12.3 Speculation

Speculative descendants are keyed by exact candidate state and planner configuration. A cache hit may make the next round immediate, but speculative generation never counts as exposure or preference evidence until shown.

## 13. Deployment modes

### 13.1 Local research mode

```text
browser
  ↕
local Python API
  ├─ in-process coordinator/planner
  ├─ SQLite
  ├─ filesystem artifacts
  └─ one local GPU renderer
```

This mode should be the reference environment for algorithm experiments and deterministic tests.

### 13.2 Hosted single-node mode

```text
web app + API
PostgreSQL
S3-compatible object store
Redis queue/cache
one or more persistent GPU workers
```

### 13.3 Scaled mode

Components can later split into independently scaled deployments:

- API/control plane;
- session coordinators;
- planner/learner workers;
- renderer pools grouped by model/hardware;
- feature workers;
- event/analytics pipeline.

The domain contracts remain the same.

## 14. API surface

A minimal HTTP/SSE API:

```text
POST   /v1/sessions
GET    /v1/sessions/{session_id}
POST   /v1/sessions/{session_id}/rounds/{round_id}/commit
POST   /v1/sessions/{session_id}/rounds/{round_id}/reroll
POST   /v1/sessions/{session_id}/worlds
POST   /v1/designs/{design_id}/star
DELETE /v1/designs/{design_id}/star
POST   /v1/designs/{design_id}/restore
POST   /v1/designs/{design_id}/export
GET    /v1/sessions/{session_id}/events
GET    /v1/models
GET    /v1/models/{profile_id}/capabilities
```

Server-sent events or WebSocket messages:

```text
round.proposed
candidate.queued
candidate.preview_ready
candidate.final_ready
candidate.failed
round.closed
session.state_changed
preference.snapshot_updated
```

Commands return the new branch version and canonical state IDs.

## 15. Preference-model lifecycle

1. Record raw action plus exposure context.
2. Validate that candidates were actually available and visible.
3. Convert the action into one typed observation.
4. Update a branch-local model asynchronously but quickly.
5. Publish an immutable snapshot.
6. Use that snapshot only for rounds created afterward.
7. Update the persistent model under a slower, separately versioned policy.
8. Evaluate new model versions offline before promotion.

The raw event remains unchanged if weighting policy changes.

## 16. Safety, provenance, and licensing

The system must record:

- model and adapter licenses;
- source and ownership declarations for uploaded references;
- whether an output used a user-provided or third-party reference;
- safety-filter revisions and decisions;
- export metadata sufficient to reconstruct provenance;
- user consent before interaction history is used for shared-model or adapter training.

The open-source code license does not override checkpoint, dataset, font, or reference-image licenses.

Safety enforcement belongs at both request and output boundaries. A renderer refusal is a valid result, and failed/blocked candidates are excluded from preference comparisons.

## 17. Privacy

Preference history can reveal sensitive information even when the UI only appears to collect image choices.

Requirements:

- private sessions by default;
- clear deletion of sessions, favorites, uploaded references, and derived user embeddings;
- separate consent for cross-user collaborative learning;
- no use of private interaction data to train shared weights by default;
- configurable retention of pointer/dwell telemetry;
- export of a user-readable event and favorite history;
- encryption in transit and at rest for hosted mode.

## 18. Observability

### Product metrics

- time to first preview and fourth preview;
- commit, reroll, star, restore, and new-world rates;
- rounds until first star/export;
- branch depth and fork count;
- stale-result rate;
- cache/speculation hit rate.

### Model metrics

- choice log likelihood and calibration;
- uncertainty calibration;
- slate diversity and duplicate rate;
- selection rate by proposal role and corner;
- direction monotonicity and transfer;
- persistent-interest collapse indicators.

### System metrics

- queue time, render time, feature time;
- GPU utilization and memory;
- batch size and warm/cold latency;
- failed/refused/cancelled jobs;
- deterministic replay pass rate;
- artifact and cache growth.

All benchmark reports include hardware, precision, resolution, batch size, step count, model digest, and warm/cold status.

## 19. Failure handling

- **One candidate fails:** keep its slot stable, show retry, and exclude it from the choice set.
- **All candidates fail:** retain the committed image; do not infer reroll.
- **Preference update fails:** continue with the previous snapshot and record degraded mode.
- **GPU worker disappears:** retry only idempotent jobs; preserve job manifests.
- **Model becomes unavailable:** retain stored assets and mark affected states as asset-only replay.
- **Object store write fails:** do not expose a candidate as commit-ready until its state and preview asset are durable.
- **Client disconnects:** rendering may finish, but no exposure is recorded until results are delivered after reconnect.

## 20. Security

- signed, expiring upload/download URLs;
- strict image type, dimensions, and decompression limits;
- prompt/reference request-size limits;
- no arbitrary checkpoint or Python-code loading from untrusted users;
- allow-listed renderer profiles in hosted mode;
- sandboxed image metadata processing;
- CSRF protection and scoped auth tokens;
- rate and budget limits per user/session;
- secrets never stored in render manifests.

## 21. Versioning

Version independently:

- public API;
- domain event schema;
- renderer capability profile;
- model manifest;
- feature encoder;
- preference learner;
- candidate planner;
- control-manifold definition;
- client interaction contract.

Old events remain readable. Migrations create new projections rather than rewriting historical evidence whenever possible.

## 22. Initial implementation phases

### Phase 0 — deterministic renderer spike

- one open checkpoint;
- exact root-noise materialization;
- four bounded perturbations;
- replay manifest and tests.

### Phase 1 — interactive vertical slice

- one canvas and four corner cards;
- commit, reroll, star, new world, last-ten restore;
- event-sourced session;
- independently streaming slots.

### Phase 2 — local preference optimizer

- feature extraction;
- Bayesian linear or PairwiseGP model;
- role-balanced slate planner;
- simulated-user evaluation.

### Phase 3 — persistent preference

- durable favorites and exports;
- multi-interest prior;
- new-world initialization;
- consent and deletion flows.

### Phase 4 — learned direction quantities

- local Jacobian/surrogate experiments;
- perceptual direction orthogonalization;
- calibrated axis views;
- optional adapter consolidation.

## 23. Architecture validation gates

A version is not ready merely because it renders images. The initial architecture is accepted when:

1. domain events reconstruct current state exactly;
2. a committed design replays at its declared reproducibility level;
3. preview cannot mutate server state;
4. two simultaneous commits cannot both advance one branch version;
5. stale slots cannot overwrite an active round;
6. reroll retains the exact parent and root-noise artifact;
7. new world changes the root without negative preference evidence;
8. restoring history creates a fork and preserves descendants;
9. planner, learner, feature, and renderer revisions are present in manifests;
10. a complete local deployment can run without proprietary infrastructure.
