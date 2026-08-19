# Implementation Readiness

**Status:** Implementation-ready v0 design, pending empirical renderer/control-basis gate  
**Last updated:** 2026-08-20

## 1. Verdict

The project is ready for a clean implementation of:

- domain contracts and event sourcing;
- the one-image/four-corner interaction;
- fake-renderer end-to-end tests;
- the normative local preference model;
- the persistent preference atlas projection;
- candidate-planner simulation.

It is **not yet justified to claim that the real image optimizer will produce compelling directions**. That depends on an empirical control-basis spike against the chosen image model.

This distinction matters:

```text
implementation readiness
    engineers no longer need to invent product or algorithm semantics

research validation
    the selected model/control manifold actually behaves well for users
```

We have enough math to implement v0. We do not have a theorem—or experimental evidence yet—that FLUX.2, Krea 2, or another checkpoint will expose the best controllable space.

## 2. Normative document order

For v0, use this precedence:

1. `INTERACTION_MODEL_V0.md` — exact user-action semantics;
2. `STATE_AND_CONTROL_CONTRACT.md` — world, design, branch, control-basis, and snapshot identities;
3. `V0_ALGORITHM_SPEC.md` — exact online optimizer and noise policy;
4. `PERSISTENT_PREFERENCE_ATLAS.md` — durable multimodal preference memory;
5. `ARCHITECTURE.md` — system boundaries and deployment;
6. `CODE_DESIGN.md` — proposed package and contract shapes;
7. `UI_DESIGN.md` and `RESEARCH_NOTES.md` — rationale and exploratory context.

When an older document presents alternatives, the normative v0 documents select one.

## 3. Decisions now locked

### Product interaction

- one committed full-canvas image;
- four stable corner candidates;
- hover/hold previews only;
- card-body click/tap commits;
- candidate favorite is an explicit separate hit target;
- global favorite always targets the committed design;
- reroll means the anchor wins against meaningfully exposed candidates;
- early reroll with insufficient exposure is a non-learning skip;
- New world is a stochastic reset, not a downvote;
- history is last ten committed branch nodes over an immutable branch forest;
- load-bearing condition changes create a new world.

### State identity

- `DesignState` contains only immutable generative provenance;
- `BranchNode` contains navigation, local-posterior, and trust-region checkpoint identity;
- candidate designs may exist and be favorited without becoming branch nodes;
- history stores branch-node IDs;
- favorites store design-state IDs;
- learner updates never mutate a design-state digest.

### Local optimization

- one absolute bounded action coordinate system per world;
- at most sixteen control dimensions in v0;
- current anchor is the outside option;
- one multinomial choice observation per round;
- Bayesian linear utility over a quadratic action feature map;
- Laplace posterior approximation;
- finite deterministic candidate pool;
- four fixed proposal roles;
- trust-region expansion on reroll and refinement after repeated commits;
- no full reinforcement learning in v0.

### Persistent preference

- a bank of evolving coherent components, not one user embedding;
- event-sourced and retractable evidence;
- commits weak, revisits moderate, favorites strong, exports strongest;
- strong novel evidence may spawn a component;
- weak evidence cannot spawn a component alone;
- dormant components persist;
- nonzero outside-prior proposal mass is mandatory;
- selected atlas exemplars become fixed world reference slots;
- candidates vary declared reference-weight coordinates rather than hidden exemplar identity;
- v0 does not initialize local weights through an unvalidated image-to-action projection.

### Seed and noise

- integer seed adjacency is meaningless;
- exact materialized root noise is authoritative;
- noise coordinates are disabled for the first real optimizer experiment;
- optional later noise movement uses bounded world-local tangent geometry;
- New world creates independent root noise and a new control basis.

## 4. Remaining empirical gates

These are experiments, not unresolved interaction semantics.

### Gate A — renderer replay

Prove that a `DesignState` can be replayed at its declared level with recorded model, runtime, noise, conditions, basis, and action.

Pass criteria:

- process-restart replay succeeds;
- no hidden defaults affect output identity;
- batch rendering does not cross-contaminate inputs;
- unsupported controls return typed refusals;
- all manifests and digests are complete.

### Gate B — useful control basis

Find a bounded world-level basis with at least eight useful dimensions.

Pass criteria:

- local sweeps are perceptually nonzero and mostly smooth;
- default-radius quartets are not near-duplicates;
- coordinate changes do not routinely destroy subject/structure unless intended;
- behavior is reproducible at fixed state;
- every coordinate has a documented compiler path;
- atlas reference slots, when present, have fixed identities and bounded weight coordinates.

If no model passes this gate, the product should not proceed by disguising random prompt/seed mutation as learned directions.

### Gate C — interaction latency

Measure on target hardware:

- time to first low-resolution candidate;
- time to all four candidates;
- hover swap latency after load;
- next-round latency with and without speculative cache;
- memory at batch size four.

Pass/fail thresholds should be based on user testing, with the current engineering budgets treated as hypotheses.

### Gate D — local learner value

Against simulated users and replayed human sessions, show improvement over:

- random action search;
- Gaussian random walk;
- top-four posterior mean without role diversity;
- no preference update.

Primary metrics:

- choice regret under known simulated utilities;
- reroll rate;
- rounds to a high-utility design;
- recovery after preference drift;
- calibration of uncertainty.

### Gate E — atlas value

Compare:

- no persistent history;
- one average centroid;
- the multimodal atlas;
- atlas with outside-prior proposals disabled.

Primary metrics:

- first-round/new-world selection rate;
- rounds to favorite/export;
- diversity across worlds;
- component proliferation and collapse;
- recovery of dormant modes.

## 5. Required contract deltas

The first code implementation should incorporate these additions to the earlier code design.

### Generative design state

```python
class DesignState(BaseModel):
    # identity, runtime, conditions, root noise, assets...
    world_id: str
    parent_design_id: str | None
    absolute_action: tuple[float, ...]
    parent_delta: tuple[float, ...] | None
    control_basis_manifest_id: str
```

It does not contain local preference, trust-region, favorite, exposure, or navigation metadata.

### Branch checkpoint

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
```

### New interaction event

```python
class RoundSkipped(BaseModel):
    kind: Literal["round_skipped"]
    round_id: str
    reason: Literal[
        "insufficient_exposure",
        "loading_abandoned",
        "client_recovery",
    ]
```

`RoundSkipped` is not converted to a preference observation.

### Separate favorite commands

```python
class FavoriteCurrentCommand(BaseModel):
    design_id: str

class FavoriteCandidateCommand(BaseModel):
    round_id: str
    candidate_id: str
```

Both ultimately produce a durable design-favorite event, but their command validation differs.

### Control-basis manifest

Add:

- bounded coordinate IDs and kinds;
- per-coordinate distance scales;
- compiler payload digests;
- calibration receipt IDs;
- zero, one, or two fixed atlas reference slots;
- immutable world-level digest.

### Persistent-atlas contracts

Add:

- `PreferenceEvidence`;
- `PreferenceComponent`;
- `PersistentPreferenceSnapshot`;
- `WorldPreferenceContext`;
- provisional weak-evidence cluster storage;
- evidence-retraction/rebuild support.

### Local-preference snapshot

Store:

```text
feature-map revision
prior precision
posterior mode
posterior covariance or Cholesky factor
observation IDs
recency policy
choice temperature
optimizer convergence receipt
```

### Candidate proposal

Add:

```text
parent branch-node ID
anchor design ID
anchor absolute action
proposed absolute action and parent delta
exposed-choice eligibility
atlas component IDs
fixed atlas reference-slot IDs
role fallback reason
planner RNG state
```

## 6. Clean pull-request sequence

### PR 1 — repository and contracts

Scope:

- Python/TypeScript workspace tooling;
- schemas and generated TypeScript types;
- pure domain events and commands;
- world/design/branch/round reducers;
- event-store interface;
- semantic hashing;
- deterministic fake renderer;
- CI with no GPU dependency.

Do not include the real model or optimizer.

Acceptance:

- all domain invariants have unit/property tests;
- schemas round-trip between Python and TypeScript;
- fake design states are content-addressed and replayable;
- events reconstruct projections deterministically;
- learner/search metadata cannot change a design-state digest.

### PR 2 — complete interaction shell

Scope:

- one canvas;
- four candidate cards;
- hover/hold preview;
- card-body commit;
- current/candidate favorites;
- reroll versus skip semantics;
- New world;
- last-ten branch restore/fork;
- SSE stream with stale-round rejection;
- Playwright tests using fake renderer.

Acceptance:

- all tests in `INTERACTION_MODEL_V0.md` pass;
- no incidental pointer event mutates preference;
- touch, keyboard, and pointer commands are equivalent.

### PR 3 — real renderer and control-basis spike

Scope:

- one model adapter;
- model/runtime/capability manifests;
- materialized root noise;
- absolute action compiler;
- world construction with fixed atlas reference slots;
- low-resolution preview and finalization;
- batch-of-four measurements;
- basis-sweep notebook/script and receipts.

Acceptance:

- Gates A, B, and C pass;
- failed capabilities produce typed refusals;
- no model-specific fields leak into product events;
- no candidate uses undeclared prompt/reference changes.

### PR 4 — local optimizer

Scope:

- quadratic feature map;
- multinomial anchor-choice likelihood;
- Laplace update;
- branch-node snapshot inheritance;
- trust region;
- Sobol/Gaussian pool;
- four proposal roles;
- simulated-user benchmark.

Acceptance:

- all normative algorithm tests pass;
- Gate D passes against frozen baselines;
- planner and posterior are exactly reproducible from manifests.

### PR 5 — persistent preference atlas

Scope:

- versioned image feature projection;
- evidence ledger and retraction;
- online components and provisional buffer;
- favorites/exports/revisits/commits weighting;
- world-context and fixed-exemplar selection;
- outside-prior proposal policy;
- export/deletion/privacy flows.

Acceptance:

- all atlas tests pass;
- Gate E is reported honestly;
- no cross-user use without consent;
- atlas-guided candidates map only to declared world coordinates.

### PR 6 — integrated research release

Scope:

- end-to-end local deployment;
- experiment dashboards and receipts;
- documented failure modes;
- reproducible sample sessions;
- model/license setup;
- contributor instructions.

Acceptance:

- a fresh machine can run the fake path without GPU;
- a supported GPU machine can run the real path;
- replay, preference, and provenance receipts are bundled with example sessions.

## 7. First code PR file-level plan

```text
pyproject.toml
pnpm-workspace.yaml
package.json
.github/workflows/ci.yml

packages/contracts/schemas/
  commands.json
  events.json
  world.json
  design.json
  branch.json
  round.json
  renderer.json
  preference.json

python/art_optimizer/domain/
  ids.py
  commands.py
  events.py
  world.py
  design.py
  branch.py
  rounds.py
  reducers.py
  hashing.py

python/art_optimizer/application/
  handlers.py
  ports.py

python/art_optimizer/persistence/
  event_store.py
  sqlite_event_store.py
  projections.py

python/art_optimizer/renderer/
  protocol.py
  fake.py

python/tests/domain/
python/tests/persistence/
python/tests/renderer/

apps/web/src/domain/generated/
apps/web/src/state/
apps/web/src/test/
```

The fake renderer should generate deterministic geometric images from the generative state digest so the entire interaction can be visually tested without pretending those images validate the real model.

## 8. Test strategy

### Domain

- property tests over arbitrary valid command sequences;
- idempotency and optimistic concurrency;
- immutable branch/fork behavior;
- exact projection rebuild;
- design-state versus branch-node identity;
- favorite evidence retraction;
- reroll versus skip distinction.

### Optimizer

- analytic gradient/Hessian checks by finite differences;
- posterior positive-definiteness;
- fixed-RNG reproducibility;
- exposure masking;
- branch snapshot inheritance;
- trust-region bounds;
- role diversity.

### Atlas

- spawn/provisional/merge/dormancy behavior;
- rebuild from evidence;
- incompatible feature revisions;
- outside-prior mass;
- world-context selection probabilities;
- fixed exemplar/reference identity;
- proposal-component provenance.

### Renderer

- world compilation;
- absolute-action capability preflight;
- replay across restart;
- batch isolation;
- typed refusal;
- rejection of hidden candidate-specific conditions;
- artifact durability before exposure.

### UI

- pointer/touch/keyboard parity;
- preview race conditions;
- candidate-favorite event propagation;
- stale stream handling;
- partial exposure choice sets;
- history branch-node restore and fork;
- failure states.

## 9. Risk register

| Risk | Consequence | Mitigation |
|---|---|---|
| No smooth real control basis | Optimizer learns noise, not useful direction | Make Gate B blocking; benchmark models/adapters |
| Absolute controls are too restrictive for an edit model | Attractive model cannot join v0 optimizer | Keep parent-relative adapter as separate experiment; do not mix semantics |
| Fixed root feels repetitive | User rerolls often despite correct learner | Enable bounded tangent-noise role after gate |
| Atlas proliferates components | Personalization becomes unstable | Strong-only spawn, provisional weak buffer, no online split |
| Atlas collapses novelty | Every world looks the same | Mandatory outside-prior mass and dedicated surprise slot |
| Hidden atlas guidance leaks outside action vector | Choice model becomes statistically incoherent | Fixed world reference slots and typed refusal |
| Quadratic utility underfits | Slow convergence | Versioned RFF/GP replacement after baseline |
| Corner thumbnails are too small | Poor choices despite good candidates | Responsive overlay sizing and 2×2 fallback experiment |
| Low-res choices reverse at final | Corrupt preference labels | Measure agreement; delay preference or use final confirmation if needed |
| Speculative rendering wastes GPU | Cost without latency benefit | Track cache hit rate and disable below threshold |
| Model/runtime updates break replay | History becomes dishonest | Immutable manifests, retained assets, declared replay level |

## 10. Questions that no longer need to block implementation

- **One prior or many?** Many evolving components.
- **Does New world forget taste?** No.
- **Does reroll downvote the world?** No; it selects the current anchor locally.
- **Are four candidate losses independent pairwise labels?** No; one multinomial observation.
- **Do adjacent integer seeds define a direction?** No.
- **Does hover train the model?** No.
- **Does selection mean permanent taste?** Primarily local; persistent weight is small.
- **Can favorite differ from branch choice?** Yes, through an explicit candidate-favorite target.
- **Which local learner ships first?** Bayesian quadratic discrete choice with Laplace posterior.
- **Does the atlas initialize local weights directly?** Not in v0; it chooses fixed world coordinates and proposal roles.
- **Can candidates secretly use different references?** No.
- **Does a prompt/reference change mutate the current branch?** No; it creates a new world.
- **Where do learner snapshots live?** On branch checkpoints, not design states.

## 11. Questions intentionally left to experiments

- which checkpoint and runtime provide the best control basis;
- exact control coordinates and their default ranges;
- final trust-region and observation-weight constants;
- whether tangent-noise controls improve or harm the experience;
- whether corner overlays beat a temporary 2×2 comparison layout;
- whether a quadratic utility model is sufficient;
- when a learned image-to-action transport prior becomes worthwhile.

These have explicit experiment gates and do not require an engineer to invent domain semantics.

## 12. Definition of ready

The design is ready to “let it cook” when that phrase means:

> Begin disciplined implementation and run the specified experiments without reopening foundational semantics.

It is not ready if that phrase means:

> Assume the selected image model and control manifold are already proven to produce high-quality personalized directions.

The correct next action is PR 1: contracts, reducers, event store, fake renderer, and CI. The real GPU model belongs after the product state machine is executable and testable.
