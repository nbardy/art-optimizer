# Unified Taste Engine Implementation Plan

**Status:** implementation design; no production code changed by this review
**Date:** 2026-08-22
**Parent decision:** [One Authoritative Taste State](14_ONE_AUTHORITATIVE_TASTE_STATE_REVIEW.md)

## Outcome

Replace the current three preference-learning paths with one server-side `TasteEngine`:

```text
typed immutable events
        ↓
deterministic versioned reducer
        ↓
TasteFamilySnapshot
        ├── active taste posterior
        ├── alternate taste posteriors
        ├── evidence membership
        ├── exemplars
        └── revision lineage
        ↓
planner, New World, branch restore, every UI
```

The completed lean v1 through Phase 4 must support:

- one eight-dimensional ideal-point model per taste;
- one active taste per branch;
- exact replay from exposed-slate preference events;
- explicit Modify, Switch, Spawn, Fork, Retraction, Split, and Merge semantics;
- automatic structure suggestions disabled by default;
- no browser-local preference learner;
- no independent persistent atlas learner.

This plan intentionally does not implement true visual attributes, a GP, a Dirichlet-process mixture, a genetic algorithm, or RL.

At user level the authoritative `TasteStateSnapshot` is a registry of scoped families. Each `TasteFamilySnapshot` is homogeneous: exactly one `scope_id`, with every component compatible with it. This resolves persistent ownership without pretending prompt-conditioned action coordinates transfer automatically.

## Decisions before code

### Decision 1: one preference authority, not one software object

Keep these layers separate:

```text
event facts
belief projection
candidate policy
renderer
UI projection
```

Only the belief projection estimates taste. A planner can optimize an acquisition function without becoming another taste model. A renderer can expose controls without learning preference. A UI can label or filter the canonical state without owning hidden evidence.

### Decision 2: a v1 taste is a mode

A taste component means one alternative preferred region in one declared representation scope.

It does not mean:

- a causal visual attribute;
- one axis of a factor model;
- a selected image;
- a candidate population;
- a branch;
- a stochastic seed.

The Concept Shelf should therefore become a Taste Shelf or be removed during the primitive test. Retaining the noun “concept” would preserve the ontology error.

### Decision 3: component assignment is explicit in v1

Every branch has one `active_taste_id`. A normal qualified choice updates that component only. The user can Switch or Spawn. The system may later suggest a structural action, but it does not silently infer one from a click.

This makes errors correctable and prevents a sparse latent mixture from diffusing every observation across uncertain modes.

### Decision 4: representation scope is exact

Current FLUX action coordinates depend on the prompt-conditioned direction bank. A compatible scope must identify at least:

```text
model repository + resolved revision
renderer revision
control codec revision
concrete direction-bank digest
prompt or prompt-family revision
action dimension
```

No posterior or action centroid crosses a scope boundary automatically. Cross-scope transport is a later, separately evaluated model.

The choice-model, reducer, prior, optimizer, and posterior-predictive revisions are model-policy metadata, not representation identity. Record them on every evidence event and component revision without making identical renderer coordinates appear incompatible merely because inference code changed.

## Canonical contracts

The names below are illustrative, but the semantics are required.

### `RepresentationScope`

```text
scope_id
model_id
model_revision
renderer_revision
control_codec_revision
direction_bank_digest
prompt_scope_id
action_dimension
```

`scope_id` should be a digest of the canonical manifest, not an informal label such as `flux2-klein/v1`.

### `PreferenceChoiceRecorded`

```text
event_id
event_sequence
schema_revision
user_id
family_id
session_id
source_branch_node_id
result_branch_node_id
round_id
active_taste_id
base_family_revision_id
base_component_revision_id
intent = "preference"
observation_weight
observation_weight_policy_revision
qualification_revision
qualification_receipt

scope_id
scope_manifest
experiment_policy_revision
planner_revision
taste_model_policy_revision
control_chart_validation_revision

anchor
    design_id
    action
    seed
    root_noise_digest
    prompt_digest
    image_digest
    comparison_context_digest

alternatives[]
    candidate_id
    design_id
    action
    slot
    role
    seed
    root_noise_digest
    seed_relation
    prompt_digest
    comparison_context_digest
    image_digest
    perceptual_equivalence_class

exposed_candidate_ids[]
qualified_candidate_ids[]
winner
    kind = "anchor" | "candidate"
    candidate_id
    design_id

created_at
```

`source_branch_node_id` identifies the branch and active taste under which the slate was generated. `result_branch_node_id` identifies the immutable checkpoint created by the command. A candidate winner points the result to the chosen design; an anchor winner creates a new checkpoint over the same design so the taste revision remains explicit.

The event must be sufficient to recompute its likelihood without loading a mutable session projection. Candidate IDs alone are insufficient.

The event may retain all generated alternatives for diagnostics, but `qualified_candidate_ids` is the exact likelihood set and must be a subset of meaningfully exposed candidates. The anchor is implicit in every qualified choice set.

Validation must require a unique event/round/candidate mapping, one winner in the anchor-plus-qualified-alternatives set, unique slots and IDs, finite actions of the declared dimension, matching family/scope/base revisions, and a nonarchived active component. For the action-only v1 likelihood, all qualified alternatives must share the anchor's prompt, scope, root seed/noise context, and comparison-context digest.

`observation_weight` is positive and server-derived from the named immutable policy; clients never choose it. `qualification_receipt` must state that exposure, duplicate, context, position-balance, and artifact checks passed. If they did not, append `NavigationSelectionRecorded` with explicit reason codes and create no component evidence membership. Do not represent “ineligible” by passing zero into a likelihood whose contract requires \(\omega_e>0\).

Exact image duplicates or candidates below the declared perceptual-distance threshold must be replaced before display when possible. If displayed, v1 may qualify at most one representative from each perceptual-equivalence class; it does not implement a grouped-choice likelihood. Otherwise multinomial logit gives a duplicated alternative extra probability mass—the red-bus/blue-bus failure—and the click likelihood depends on accidental duplicate count.

### Non-preference events

```text
MoreVarietyRequested
BrokenRenderReported
PreviewOpened
FavoriteToggled
WorldRequested
DesignRevisited
NavigationSelectionRecorded
```

These events can affect UI, rendering, metrics, bookmarks, or provenance. They do not update a taste posterior.

`NoneOfTheseSelected` is different. It records a `PreferenceChoiceRecorded` whose winner is the anchor, after exposure qualification. The UI must never send that event under the label “Reroll.”

### Structural events

```text
TasteSpawned
TasteSwitched
TasteForked
BranchForkedFromCheckpoint
TastePromoted
TasteDormancyChanged
TasteExemplarLinked
TasteExemplarUnlinked
TasteSplit
TasteMerged
EvidenceReassigned
EvidenceExcludedFromBranch
EvidenceGloballyInvalidated
```

Every structural event records:

- source revision IDs;
- affected component IDs;
- exact evidence IDs or deterministic partition rule;
- actor and reason;
- whether the action was explicit, suggested-and-confirmed, or administrative;
- resulting revision IDs.

### `TasteComponentRevision`

```text
component_id
component_revision_id
family_id
scope_id
status = provisional | established | dormant | archived

posterior_mean[d]
posterior_covariance[d,d]
base_prior_revision
base_prior_mean[d]
base_prior_covariance[d,d]
choice_temperature
utility_curvature_revision
posterior_predictive_revision

evidence_event_ids[]
exemplar_design_ids[]
observation_count
effective_evidence_mass

parent_component_revision_ids[]
created_by_event_id
created_at
```

The component ID names a continuing taste identity. The revision ID names one immutable belief state.

### `TasteFamilySnapshot`

```text
family_id
user_id
scope_id
reducer_revision
family_revision_id
last_event_sequence

components[]
lineage_edges[]

created_at
updated_at
```

Posterior covariance and utility curvature must use different fields and names. They answer different questions:

- posterior covariance: how uncertain are we about the ideal point?
- metric/curvature: how quickly does preference fall away from that point? Approximate geometric width scales with \(Q^{-1/2}\).

### `TasteStateSnapshot`

```text
user_id
reducer_revision
state_revision_id
last_event_sequence
families_by_scope{}
branch_taste_heads{}
updated_at
```

`TasteFamilySnapshot.scope_id` is mandatory, and every contained component must assert the same scope. `branch_taste_heads` contains immutable mappings from branch-node IDs to `(family_id, family_revision_id, component_id, component_revision_id)`; the session projection chooses its current branch. Switch or preference update creates a new branch checkpoint rather than mutating an old pointer. Cross-scope names or user-visible links may live in the registry, but they carry no shared numeric posterior until a transport model is explicitly introduced.

## The reducer

Implement the reducer as a pure, deterministic module. I/O and locking live outside it.

```python
def reduce_taste_state(state, event, *, policy):
    require(event.schema_revision in policy.accepted_event_schemas)
    require(event.event_sequence == state.last_event_sequence + 1)

    match event.kind:
        case "preference_choice_recorded":
            base = state.branch_taste_heads[event.source_branch_node_id]
            require(event.scope_id in state.families_by_scope)
            require(event.family_id == base.family_id)
            require(event.active_taste_id == base.component_id)
            require(event.base_family_revision_id == base.family_revision_id)
            require(event.base_component_revision_id == base.component_revision_id)
            state = add_evidence_refit_and_create_result_head(state, event, policy)

        case "taste_switched":
            state = create_switched_branch_head(state, event)

        case "taste_spawned":
            state = create_provisional_component_and_branch_head(state, event, policy)

        case "taste_forked":
            state = fork_component_identity_and_branch_head(state, event)

        case "branch_forked_from_checkpoint":
            state = create_branch_head_from_historical_revision(state, event)

        case "taste_promoted" | "taste_dormancy_changed":
            state = revise_component_lifecycle(state, event)

        case "taste_exemplar_linked" | "taste_exemplar_unlinked":
            state = revise_component_metadata_without_refitting(state, event)

        case "taste_split":
            state = partition_and_jointly_refit(state, event, policy)

        case "taste_merged":
            state = union_and_jointly_refit(state, event, policy)

        case "evidence_excluded_from_branch" | "evidence_reassigned":
            state = rebuild_affected_lineage(state, event, policy)

        case "evidence_globally_invalidated":
            state = rebuild_every_descendant_containing_event(state, event, policy)

        case kind if kind in policy.non_preference_event_kinds:
            state = state  # retained fact, zero taste effect

        case _:
            raise UnsupportedEventKind(event.kind)

    return state.with_cursor(event.event_sequence)
```

The real implementation should return a new state rather than mutate its input. Randomness, if later needed for approximate inference, must use a seed recorded in the structural event.

After every event, validate:

- every branch head resolves to an existing, nonarchived, scope-compatible component revision;
- every family contains only its declared scope;
- posterior covariance and \(Q\) are symmetric positive definite and \(\tau>0\);
- evidence dimension, scope, model policy, and base-prior provenance are compatible;
- revision parents exist and the lineage graph is acyclic;
- split siblings are disjoint, merge evidence is deduplicated, and no component evidence closure contains an event twice;
- result revision IDs and branch-node IDs are new and source/base revision IDs exist.

### Exactly-once rule

A preference event ID may occur at most once in the evidence closure of any one component revision. Forked heads intentionally share an immutable ancestral evidence prefix; that is versioned counterfactual lineage, not a second update inside either posterior. Split children partition the parent's evidence rather than duplicate it, Merge unions and deduplicates, and Reassignment removes before adding.

The storage constraint is therefore unique on `(component_revision_id, event_id)`, plus reducer assertions that split siblings are disjoint and merge unions contain each ID once. A global unique constraint on `event_id` across every fork would be incorrect.

“Undo on this branch” appends `EvidenceExcludedFromBranch` and creates a new descendant revision; sibling forks retain their shared ancestral fact. `EvidenceGloballyInvalidated` is a rarer administrative correction for a corrupt or semantically invalid source event and rebuilds every descendant that contains it. `EvidenceReassigned` must name the exact family head/lineage it changes. A generic Retraction event would be dangerously ambiguous in a revision DAG.

### Incremental processing versus joint refit

Ordinary Modify adds the new event ID to the active component's evidence set, then refits one joint MAP from the materialized fixed base prior and every assigned event. The previous MAP is only a numerical warm start; its Laplace covariance is not reused as a new prior.

Retraction, reassignment, split, merge, and reducer-revision migration use the same operation over their resulting evidence sets. Because the ideal-point objective is strictly concave, the evidence set and model revision determine one MAP independent of input enumeration order, within declared numerical tolerance.

The tests must establish:

\[
F_r(F_r(S_0,e_1),e_2)
=
\operatorname{Fold}_r(S_0,[e_1,e_2]).
\]

Snapshots are caches. A mismatch with full replay is a correctness failure.

## Ideal-point component API

Add a component model whose public surface is narrower than the current learner:

```python
class IdealPointChoiceModel:
    def predict_choice_given_target(self, slate, target): ...
    def posterior_predictive_choice(self, slate, *, approximation): ...
    def predict_relative_utility(self, anchor, actions): ...
    def fit_evidence(self, observations, *, warm_start=None): ...
    def sample_target(self, rng): ...
    def snapshot(self): ...
```

The fixed settings belong to a versioned model policy:

```text
dimension = 8
Q = calibrated positive-definite matrix
temperature = fixed value
prior mean
prior covariance
Laplace optimizer tolerances
posterior-predictive approximation revision and sample count
```

Here \(Q\) is utility curvature in the taste-model policy. A measured control-chart or perceptual metric may inform its prior value, but the two are not the same ontology: changing \(Q\) refits preference evidence and does not invent a new renderer/control scope.

For Gaussian posterior \(q(\theta)\), the proper predictive choice probability is:

\[
p(y\mid A,q)
=
\int p(y\mid A,\theta)q(\theta)\,d\theta.
\]

This logistic-normal integral has no general softmax-at-the-mean identity. Use a deterministic, versioned approximation for calibration, prequential scores, and structural suggestions. A practical v1 is scrambled-Sobol normal sampling with a fixed sample count and a seed derived from the component revision plus slate digest. A plug-in MAP softmax may remain a fast planner heuristic, but must not be reported as a calibrated posterior predictive.

Do not add a forgetting factor to the first component model. Forgetting confounds two different hypotheses:

- uncertainty should decay as evidence accumulates;
- taste itself changes over time.

Represent intentional change by Switch, Fork, Spawn, or a later explicit dynamics model. A silent forgetting factor makes exact historical interpretation impossible.

### Numerical checks

For every update:

- stabilize and symmetrize covariance;
- check finite logits and probabilities;
- require \(Q\succ0\) with a declared minimum eigenvalue;
- use damped Newton or a trusted convex optimizer;
- record convergence diagnostics;
- record the posterior-predictive approximation revision used by every prequential receipt;
- never clip the posterior mean silently as if clipping were Bayesian inference.

Actions may remain bounded. Proposal projection into `[-1,1]^d` is a planner operation.

## Lifecycle algorithms

### Modify

1. Validate command idempotency and mutation version.
2. Freeze the exact exposed slate.
3. Allocate `result_branch_node_id` and append one `PreferenceChoiceRecorded` event naming both source and result branches.
4. Add the event once to the active component's evidence set and jointly refit it from its fixed base prior.
5. create a new component revision and family revision;
6. point the new branch node at that revision;
7. atomically store event and projections.

Favorite, revisit, and export must not add another likelihood term for the same choice. Favorite remains a user-level bookmark. Representative exemplars can be derived from the component's qualified winning evidence; a user-curated exemplar requires a typed `TasteExemplarLinked` event naming the taste and changes metadata, not the posterior.

### Spawn

The initial command should be explicit:

```text
Start a new taste here
```

Create:

\[
\theta_{new}\sim
\mathcal N(a_{seed},\sigma_{spawn}^2Q^{-1}),
\]

with broad declared uncertainty. `a_seed` is the chosen/current action inside the same representation scope.

The explicit `TasteSpawned` command is the structural signal that centers this prior. Leave the preceding choice assigned where it was; using that same outcome both to center an empirical prior and as reassigned likelihood evidence would double-use it. A later `EvidenceReassigned` operation must refit from a fixed outcome-independent base prior.

The spawned component becomes the new branch's active pointer immediately while its lifecycle status remains `provisional`. `TastePromoted` changes it to `established` for durable shelf/display semantics; branch activation and lifecycle status are separate.

### Switch

Change `active_taste_id` and generate a new slate under that component. The pointer change carries zero choice weight.

### Fork

`TasteForked` creates a new component identity that shares the parent's immutable evidence ancestry and starts a branch-local provisional taste. Only subsequent evidence diverges; shared ancestry is referenced rather than copied as duplicate updates. Promotion is explicit.

`BranchForkedFromCheckpoint` is different: it creates a new navigation/branch head pointing at the same historical component identity and revision. It does not claim a new taste. These operations require different events and buttons.

### Split

Inputs:

- one parent component revision;
- two disjoint evidence-ID sets whose union is the parent's active evidence;
- labels or a deterministic proposal partition;
- confirmation metadata.

Algorithm:

1. instantiate two children from the same base prior;
2. replay each partition in event order from the parent's materialized base prior;
3. verify minimum evidence, independent anchors, and scope compatibility;
4. compute prequential or held-out predictive scores;
5. archive the parent and activate children only if the decision rule passes;
6. retain a reversible lineage event.

No coordinate-wise division, posterior averaging, or random clustering of chosen actions is a split.

### Merge

Inputs must have compatible scope and model revisions. Their materialized base priors must also match, unless the confirmed merge event declares a new canonical merge prior.

1. union evidence IDs;
2. deduplicate IDs;
3. replay from the common prior, or from the explicit merge prior recorded in the event;
4. compare predictive loss with the separate models;
5. require confirmation for named modes;
6. archive parents and retain lineage.

For v1, reject merges with incompatible base priors. A later explicit merge-prior policy must be versioned and evaluated; silently averaging prior or posterior parameters is forbidden.

### Automatic suggestions, later

The system may eventually suggest Spawn or Split after sustained low posterior-predictive likelihood, not one surprising click.

For a window \(W\), track pre-update surprise:

\[
S_W=-\sum_{t\in W}\log P(y_t\mid A_t,T_{active,t-1}).
\]

A suggestion should require all of:

- unusually high surprise over several independent rounds;
- a proposed alternative with positive held-out/prequential gain after a complexity penalty;
- minimum evidence in each child;
- evidence across multiple controlled anchors and independent same-context rounds;
- a stable separation under standardized probe slates;
- user confirmation.

Do not enable automatic application in the first family experiment.

## Branch and history semantics

Replace `BranchNode.posterior` with references:

```text
family_id
active_taste_id
taste_family_revision_id
component_revision_id
```

PreferenceChoice, NoneOfThese, Switch, Spawn, and a checkpoint fork each create a new immutable branch node, even when the design anchor itself does not change. The session's `current_branch_node_id` is the mutable navigation pointer. A checkpoint fork selects the exact historical family/component revision and creates a sibling head from it; it does not delete later events or revisions.

Separate two commands that are currently easy to conflate:

```text
Revisit this image
    change navigation anchor; keep latest taste state

Fork branch from this checkpoint
    restore historical image and exact historical taste revision

Fork this taste
    create a new provisional taste identity with shared evidence ancestry
```

If the product retains only one restore command, its effect on taste must be visible in the label and confirmation.

## Planner integration

Replace `PlannerContext.atlas_bias_action` and `alternate_atlas_action` with:

```text
active_component_posterior
alternate_component_summaries
representation_scope
noise_policy
perceptual_duplicate_policy
```

For posterior \(\theta\sim\mathcal N(m,C)\), the primitive planner can assign four roles:

1. **Exploit:** nearest valid action to \(m\) within the current trust region.
2. **Posterior sample:** sample \(\tilde\theta\sim\mathcal N(m,C)\), then propose toward it.
3. **Uncertainty-informed query:** use \(QCQ\) to locate uncertain directions, construct balanced alternatives near predicted indifference, then choose the slate by expected Fisher information or expected log-determinant reduction.
4. **Alternate/outside:** propose near another explicit taste or outside the known family.

Relative-utility variance is a useful proposal primitive:

\[
\operatorname{Var}
\left[
\frac{u(a)-u(a_0)}{\tau}
\right]
=
\frac1{\tau^2}(a-a_0)^TQCQ(a-a_0).
\]

It is not itself expected information. The final acquisition score must include choice probabilities through \(Q\operatorname{Cov}_{p_\theta}(a)Q/\tau^2\); highly saturated comparisons can have poor Fisher information despite a large variance direction.

The planner still needs perceptual output checks. Four distinct actions do not guarantee four distinct images.

### Seed and command policy

Keep these typed:

| Command | Candidate/noise effect | Taste effect |
|---|---|---|
| choose candidate | commit that already rendered design; propose next slate | one update only if the exposed slate passed same-context and position-balance qualification; otherwise record navigation only |
| None of these | keep anchor; propose next slate | one anchor-wins update only for a qualified same-context slate |
| More variety | choose a new common stochastic root or otherwise change noise policy | none for the request or any mixed-root comparison |
| New World | create new stochastic root under selected taste | none |
| broken image | replace/repair candidate | none |

After More Variety establishes a new root, a later preference-bearing slate may still qualify if its anchor and every alternative share that same new root and all other scope fields match. The neutrality applies to the variety request itself, not permanently to the resulting world.

Clicking a candidate should continue to select the exact rendered image shown. If the desired command is “extract an attribute from this image and generate a different image,” that needs a different event, attribute model, and renderer contract. Do not overload candidate selection again.

Candidate positions and role labels must be randomized or counterbalanced. The v1 likelihood has no slot-bias term; fixed placement would otherwise teach the taste target to absorb UI-position preference.

## UI projection

Remove `ConceptLibrary` from browser ownership. The server snapshot should expose a compact taste view:

```text
active taste
branch-active marker
provisional/established/dormant lifecycle status
evidence count
uncertainty summary
representative exemplars
lineage
compatible scope
```

Recommended initial controls:

```text
Choose
None of these
More variety
Start new taste here
Switch taste
Fork this taste
Fork branch from checkpoint
Undo preference on this branch
Globally invalidate corrupt event (administrative only)
```

Do not show:

- auto-generated attribute labels;
- additive lane strengths;
- a Recast composition;
- confidence numbers that combine evidence support, opposition, and activation;
- concepts created from one click.

### What should happen to the four UI routes

If the routes are only presentation variants, sharing the same canonical state is correct and should be stated honestly.

If they are intended to test genuinely different interaction hypotheses, each route must resolve to a versioned `ExperimentPolicy` that declares:

```text
command semantics
candidate policy
noise policy
renderer mode
learner/reducer revision
component lifecycle rules
candidate count and scheduling
metrics
```

Different policy treatments should use isolated sessions/family projections. They may share immutable artifacts or exportable facts, but a choice elicited under one command contract must not silently mutate another treatment's belief.

The concrete engine/data/planner/UI factorial design is specified in [Taste Engine, Data Model, and UI Ablation Matrix](14B_TASTE_ENGINE_UI_ABLATION_MATRIX.md). “One authority” applies within an assigned live treatment; it does not prevent the repository from hosting several engines or running compatible engines in read-only shadow mode.

## Persistence and transactions

The present storage calls the SQLite table an event store, but the session projection is operationally authoritative and the atlas is saved separately. The new path must make the event history sufficient for preference replay.

Use one database transaction to:

1. validate the expected user `TasteState` and session revisions;
2. append the immutable interaction event;
3. allocate the next per-user event sequence and derive the next taste-state/family revision;
4. derive the next session/branch projection;
5. persist both projections;
6. save the idempotent command result.

The current `events` table has a global integer primary key but stores and indexes only `session_id`; it has no user-level ordering or concurrency contract. Taste memory crosses sessions, so a per-session `asyncio.Lock` cannot protect it.

Require:

- `UNIQUE(user_id, event_sequence)` and globally unique event UUIDs;
- compare-and-swap on `expected_taste_state_revision_id`, or a `BEGIN IMMEDIATE` single-writer transaction that validates that revision before allocation;
- retry from a freshly loaded state after a CAS conflict;
- idempotent command IDs that survive the retry;
- one canonical ordering for simultaneous commands from different sessions.

Without that contract, two active sessions can both read revision \(r\), independently write \(r+1\), and lose one vote even though each session lock behaved correctly.

Recommended logical tables:

```text
interaction_events
taste_state_projections
taste_family_projections
taste_component_revisions
taste_evidence_membership
session_projections
command_results
```

They may initially be implemented with JSON projections, but constraints for unique event IDs, ordered sequences, and evidence membership should live in SQLite rather than only in Python assertions.

## Legacy-data migration

Do not merge the three derived legacy states. That would preserve their contradictory semantics and double-count some clicks.

Migration policy:

1. archive the existing session, atlas, and browser concept formats unchanged;
2. reconstruct only raw committed-choice events whose anchor, full qualified slate, action vectors, scope, and winner can be established;
3. exclude legacy rerolls by default because the old label conflated novelty with anchor preference;
4. retain favorites as bookmarks/exemplars, not additional choice likelihood terms;
5. do not import atlas centroids as posterior observations;
6. do not import browser concept directions as tastes or attributes;
7. mark reconstructed events `legacy_inferred` and emit a migration receipt;
8. start a fresh family if exact reconstruction is not possible.

A clean fresh baseline is scientifically preferable to a falsely precise migration.

## Concrete file map

| File | Change |
|---|---|
| `art_optimizer/domain.py` | add event, scope, taste-state/family, component-revision, and lifecycle contracts; persist resolved model and concrete direction-bank identity on designs/worlds; replace branch posterior with revision references |
| `art_optimizer/preference.py` | add `IdealPointChoiceModel`; retain current model only as an experimental baseline |
| `art_optimizer/taste.py` | new pure reducer, replay, structural operations, and invariants |
| `art_optimizer/event_store.py` | add user-level interaction log and atomic family/session projection transaction |
| `art_optimizer/service.py` | emit typed events once; make `TasteEngine` the only preference authority |
| `art_optimizer/planner.py` | consume active/alternate components; remove atlas guidance inputs |
| `art_optimizer/embedding_conditioning.py` | materialize a canonical manifest and digest for each concrete prompt-conditioned direction bank |
| `art_optimizer/diffusers_renderer.py` | expose the resolved checkpoint revision and attach the direction-bank manifest/digest to every render artifact |
| `art_optimizer/rendering.py` | carry representation-scope provenance through artifact metadata and cache manifests |
| `art_optimizer/atlas.py` | retire as preference learner; optionally retain a read-only legacy migrator |
| `art_optimizer/static/experiment_core.js` | remove `ConceptLibrary`; consume server taste projection only |
| UI modules | rename shelf/lanes to taste/history views or hide them in the primitive treatment |
| tests | add replay, lifecycle, synthetic-oracle, cross-UI, and migration coverage |

The 13-dimensional image statistics may remain renderer diagnostics. They must not silently define preference modes.

## Implementation sequence

### Phase 0 — freeze the baseline

- tag the current controlled-search treatment and its database schema;
- retain the existing 44D learner for comparison only;
- capture deterministic procedural fixtures and representative FLUX event traces;
- document that current concepts and atlas are legacy projections.

### Phase 1 — truthful events

- split `MoreVariety` from `NoneOfThese`;
- make the choice event self-contained;
- store scope and policy manifests;
- establish event-fold replay and joint-refit equivalence;
- add atomic event plus projection persistence.

No family behavior should ship before this phase is correct.

### Phase 2 — one taste, shadow evaluation

- implement the 8D ideal-point model with \(K=1\);
- replay qualified choice traces into it;
- compare prequential predictions with the current 44D model;
- keep the current model authoritative during shadow evaluation;
- verify numerical and replay invariants.

Shadow output is diagnostic only. It must not influence candidates until cutover.

### Phase 3 — authority cutover

- make the scoped family selected from the authoritative `TasteState` the sole planner input;
- stop atlas updates;
- stop browser Concept Library updates;
- expose family revision and active component in every snapshot;
- make New World initialize from the active component only when the new world resolves to the same representation scope; otherwise create a fresh scoped family or use a separately validated transport.

At the end of this phase, exactly one state can answer “what do we think the user likes?”

### Phase 4 — explicit family operations

- add Spawn, Switch, Taste Fork, Branch Fork, Dormancy, branch-local Evidence Exclusion, global invalidation, and Evidence Reassign;
- add server-rendered Taste Shelf cards from canonical components;
- add Split and Merge as replay operations behind an expert/debug surface;
- keep auto-split and auto-merge disabled.

### Phase 5 — structure-learning experiment

Only after explicit two-mode behavior beats a single-mode baseline:

- implement spawn/split suggestions from prequential surprise;
- evaluate false-spawn and false-split rates;
- require confirmation;
- keep automatic destructive structure changes disabled.

### Phase 6 — representation expansion

Only after the control-basis gate and action-space transfer tests:

- test a nonlinear preference GP per mode;
- test a versioned visual feature representation;
- learn an explicit visual-to-control transport or use reference conditioning;
- then revisit composable attributes.

RL and automatic nonparametric mixtures remain outside this sequence until a concrete failure and metric justify them.

## Verification

### Mathematical unit tests

- finite-difference checks for gradient and Hessian;
- strict negative-definiteness of the log-posterior Hessian;
- covariance symmetry and positive definiteness;
- slate permutation invariance;
- common-utility-offset invariance;
- anchor and candidate winner likelihoods;
- exposure-mask qualification;
- synthetic recovery of a known ideal point;
- invariance of the final joint MAP to evidence enumeration order within numerical tolerance;
- failure to claim recovery when probes do not span all dimensions.

### Reducer property tests

- incremental event-fold plus joint refit equals full event replay;
- duplicate event IDs do not update twice;
- Switch changes no posterior;
- More Variety, preview, favorite, revisit, and New World change no posterior;
- qualified None of these performs exactly one anchor-wins update;
- branch-local evidence exclusion removes one event only from the targeted descendant lineage;
- global invalidation removes the corrupt event from every affected descendant;
- TasteFork and BranchFork preserve their distinct identity/evidence semantics;
- split partitions without duplication or loss;
- merge equals replay over the union;
- branch restore resolves an immutable historical revision;
- incompatible scopes are rejected.

### Integration tests

- every UI sees the same `family_revision_id` for one session;
- browser local storage contains no learned taste state;
- restart from SQLite reproduces the exact posterior and lineage;
- command retry returns the same result without a second event;
- session and family projections advance atomically;
- two concurrent sessions updating one user `TasteState` produce two ordered events with no lost update under CAS/retry;
- planner candidate roles cite the component revision they used;
- role-to-slot assignment is randomized or counterbalanced and logged;
- legacy migration produces a receipt and never imports ambiguous evidence silently.

### Synthetic family tests

Use generated choice oracles before human evaluation:

1. one stationary ideal point;
2. two alternating ideal points with explicit Switch labels;
3. one drifting target;
4. noisy and inconsistent choices;
5. an unidentifiable slate sequence;
6. a control-scope change.

Measure prequential log loss, target error where identifiable, calibration, false structural suggestions, evidence purity, and replay equality.

## Experimental gates

### Gate A — control basis

Before interpreting any taste component:

- axis effect size and smoothness;
- direction Gram matrix/rank/conditioning;
- perceptual duplicate rate;
- cross-seed behavior;
- prompt-conditioned scope identity;
- image quality and artifact rate.

If this fails, fix or replace the control representation. Preference sophistication cannot compensate.

### Gate B — one component

Compare:

```text
random/local planner
current 44D quadratic baseline
8D ideal-point TasteEngine
```

Primary metrics:

- prequential choice log loss;
- calibration;
- time/choices to a user-accepted design;
- time to first useful candidate;
- recovery after one inconsistent vote;
- posterior contraction only in explored directions.

Run two distinct comparisons:

1. **Offline/shared-slate shadow scoring:** both models predict the same chronological logged slates before seeing each outcome. Prequential log loss and calibration are directly comparable here.
2. **Online adaptive-policy evaluation:** each model steers different future slates, so time-to-accepted-design and usefulness require randomized or counterbalanced live assignment, matched budgets, and treatment-aware analysis.

Before collecting results, preregister a non-inferiority margin for prequential log loss and a minimum usefulness threshold. Interpretability, replayability, and parameter count are separate required properties; they cannot excuse an arbitrarily worse predictive model.

### Gate C — explicit two-taste family

Alternate two clearly different instructed goals and require the user to Switch explicitly. Compare:

- one component that averages both histories;
- two explicit components;
- two components plus an alternate-taste candidate.

Measure predictive likelihood, mode contamination, switch recovery, user comprehension, and whether New World reflects the chosen taste.

### Gate D — structural suggestions

Use hidden synthetic two-mode sequences and human sessions. Measure:

- false spawn/split suggestions under one stable taste;
- missed suggestions under two modes;
- evidence required before a useful suggestion;
- user acceptance/correction rate;
- predictive gain after confirmation.

Do not promote the feature if it recreates one component per click.

### Gate E — cross-world transfer

Separately test:

```text
same prompt, new seed
related prompt, new direction bank
unrelated prompt
new model/control codec
```

Never report “persistent taste” as one aggregate metric across these conditions.

## Cutover acceptance criteria

The unified learner is complete only when all are true:

1. One qualified click creates exactly one immutable preference event.
2. Full replay reproduces the online family snapshot bit-for-bit or within declared numerical tolerance.
3. The planner, New World, branch state, and every UI cite the same family/component revision.
4. Atlas and browser Concept Library no longer mutate preference state.
5. More Variety and None of these have different event and likelihood semantics.
6. Favorites and revisits cannot double-count a prior choice.
7. Spawn/Switch are explicit and reversible.
8. Split/Merge operate through evidence replay and preserve lineage.
9. Incompatible control scopes cannot pool numeric actions.
10. Product copy says “taste mode/region,” not “learned attribute,” until attribute tests pass.
11. The one-component primitive meets the preregistered prequential non-inferiority margin and live usefulness threshold versus the 44D baseline; interpretability and replayability also pass their independent criteria.
12. A two-component explicit family beats a one-component average before automatic structure learning begins.

## Final handoff

The first coding PR should not attempt the whole plan. Its bounded objective should be:

> Add self-contained typed choice events, a pure replayable 8D ideal-point `TasteEngine` with \(K=1\), and shadow-evaluation tests. Do not yet change candidate generation or expose family controls.

The second PR can cut planner/New World authority over after the shadow receipts pass. The third can remove the atlas and browser learner and add explicit family operations.

That sequence preserves the controlled baseline, produces falsifiable receipts at each boundary, and prevents another broad UI claim from outrunning the primitive underneath it.
