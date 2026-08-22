# Taste Engine, Data Model, and UI Ablation Matrix

**Status:** experimental architecture and evaluation plan
**Date:** 2026-08-22
**Depends on:** [One Authoritative Taste State](14_ONE_AUTHORITATIVE_TASTE_STATE_REVIEW.md) and [Unified Taste Engine Implementation Plan](14A_UNIFIED_TASTE_ENGINE_IMPLEMENTATION_PLAN.md)

## Decision

Yes: Art Optimizer should deliberately test different taste engines, different engine-owned data projections, different internal subfunctions, different planners, and different UIs.

The constraint is:

> One engine is authoritative inside one live treatment. Many versioned engines may be compared across isolated treatments or run read-only in shadow from the same immutable facts.

This reconciles two goals that otherwise sound contradictory:

```text
product/session correctness
    one preference owner, one pinned meaning of each command

research breadth
    many replaceable engines, projections, planners, and UIs
```

The project should not crown the ideal-point family by architecture decree. It should make it the first lean contender and build a harness capable of falsifying it.

## The common kernel versus the ablated parts

Some facts must remain common so treatments can be audited and compared. Everything inferential may vary behind a versioned boundary.

### Common immutable observation envelope

Every treatment should be able to record:

```text
who / session / treatment
what anchor and alternatives actually appeared
which alternatives were meaningfully exposed
what the user did
command intent
actual image and action identities
prompt/model/control/noise context
presentation position and timing
artifact/duplicate qualification
representation and policy revisions
```

This is a factual envelope, not a universal learner schema. A treatment may add typed payloads such as scalar ratings, attribute annotations, pairwise reasons, image masks, or preservation requests.

### Treatment-owned projections

The same qualified event stream may produce very different projections:

```text
8D ideal-point posterior
44D quadratic utility posterior
GP subjective function
finite family of explicit modes
latent mixture responsibilities
visual-exemplar memory
sequence-conditioned preference prior
factor/attribute posterior
drift or changepoint state
```

No projection is silently converted into another. A projection is identified by:

```text
engine_id
engine_revision
projection_schema_revision
model_policy_revision
representation_scope_id
base_prior_revision
source_event_cursor/digest
```

## Treatment composition

Define one treatment as a pinned bundle:

\[
\mathcal T
=
(O,R,L,S,A,N,U,M),
\]

where:

| Symbol | Axis | Examples |
|---|---|---|
| \(O\) | observation contract | multi-choice, rating, pairwise, attribute annotation |
| \(R\) | preference representation | 8D action, visual embedding, joint action/visual, sequence |
| \(L\) | component learner | none, ideal point, quadratic, GP, exemplar model |
| \(S\) | structure/lifecycle | one mode, explicit family, latent mixture, drift/factors |
| \(A\) | acquisition/planner | random, local, Thompson, expected information, alternate mode |
| \(N\) | renderer/noise policy | fixed common root, new common root, parent-conditioned edit |
| \(U\) | UI and command vocabulary | truthful chooser, Taste Shelf, implicit mode UI, factor composer |
| \(M\) | metrics/stopping policy | log loss, usefulness, latency, structure quality, comprehension |

`ExperimentPolicy` should contain this complete bundle and a stable `treatment_id` digest. A route name is not a treatment.

## Engine protocol

The first implementation can use a Python protocol rather than a plugin system:

```python
class TasteEngine(Protocol):
    engine_id: str
    engine_revision: str
    projection_schema_revision: str

    def initialize(self, scope, prior, treatment) -> EngineProjection: ...
    def validate_event(self, projection, event) -> QualificationReceipt: ...
    def observe(self, projection, event) -> EngineProjection: ...
    def predict(self, projection, slate, *, before_event) -> PredictiveReceipt: ...
    def planner_view(self, projection) -> PlannerTasteView: ...
    def ui_view(self, projection) -> UITasteView: ...
    def replay(self, events, treatment) -> EngineProjection: ...
    def validate_projection(self, projection) -> ValidationReceipt: ...
```

The protocol deliberately does not require one common posterior type. `EngineProjection` is a discriminated, engine-owned schema stored in a namespaced record.

The common system is responsible for:

- immutable events;
- treatment assignment;
- idempotency and concurrency;
- artifact provenance;
- before-outcome prediction receipts;
- projection namespacing;
- UI/engine compatibility checks;
- metric collection.

The engine is responsible for the meaning and replayability of its own state.

## Engine subfunctions worth ablating

Do not compare only monolithic engine names. The useful scientific question is which primitive causes the difference.

| Subfunction | Lean default | Alternatives | Main failure tested |
|---|---|---|---|
| evidence qualification | same-context exposed slate | context-aware likelihood; visual-only choice | nuisance attribution |
| representation | validated 8D action | visual embedding; joint action/visual; history sequence | control chart misses taste |
| utility form | ideal point | 44D quadratic; GP; neural scorer | one-basin bias |
| posterior approximation | joint MAP + Laplace | MCMC/QMC; variational; bootstrap | uncertainty miscalibration |
| component assignment | explicit active mode | soft responsibilities; changepoint inference | user burden versus mode contamination |
| component count | fixed/explicit | penalized spawn/split; nonparametric prior | underfit versus fragmentation |
| temporal behavior | stationary component | drift state; recency kernel; changepoint | inspiration-driven change |
| cross-world memory | exact-scope family | visual exemplars; learned transport; sequence prior | prompt/basis transfer |
| proposal policy | target/uncertainty roles | random; Thompson; Fisher; evolutionary/MAP-Elites | query quality |
| duplicate handling | replace/exclude | perceptual grouping likelihood | MNL duplicate bias |
| branch semantics | immutable revision DAG | latest-only state; explicit counterfactual forks | recoverability cost/value |
| explanation/UI projection | exemplars + uncertainty | axis score gallery; mode map; natural-language summary | comprehension/trust |

This table also prevents a common failure: comparing an ideal-point engine with one planner against a GP engine with a different UI and then attributing the whole result to the learner.

## Candidate engine families

### E0 — no-learning control

```text
state
    current anchor only

planner
    random or calibrated local/global proposals
```

Purpose: establish whether any learner beats a good exploration baseline.

### E1 — legacy 44D quadratic baseline

Use the current exposure-aware multinomial learner, but with truthful `NoneOfThese` and `MoreVariety` semantics and the same qualified slates as other treatments.

Purpose: measure whether its nonlinear flexibility earns the extra 36 parameters.

### E2 — one 8D ideal-point component

```text
state
    one fixed-scope target posterior

fit
    joint MAP + Laplace from complete choice history
```

Purpose: test the smallest interpretable preference primitive.

### E3 — explicit ideal-point family

```text
state
    several E2 components
    explicit branch-active component
    immutable lineage
```

Purpose: test whether retaining alternative goals beats averaging them.

### E4 — GP per explicit taste

One preference GP or scored-example GP per user-created taste, with a declared kernel and posterior-predictive acquisition. This is structurally inspired by the explicit subjective-function discipline in Shimizu, while multi-choice likelihood and family lifecycle remain Art Optimizer decisions.

Purpose: test whether nonconvex utility is needed after the control basis is validated.

### E5 — visual-exemplar engine

```text
state
    selected/qualified image embeddings
    explicit negative or comparative context
    retrieval/exemplar neighborhoods
```

Purpose: test persistent visual memory without pretending action coordinates transfer across prompts.

Limitation: it cannot steer the current renderer without oversample-and-rerank, reference conditioning, or a learned visual-to-control transport.

### E6 — joint action/visual engine

Maintain a visual preference model plus a scope-specific action head or surrogate mapping from controls to visual features.

Purpose: close the loop between what is visually preferred and what the generator can express.

This is more faithful to the product ambition but substantially more complex than E2/E3.

### E7 — latent mode/filter engine

Infer component responsibilities or changepoints rather than asking the user to Switch explicitly.

Purpose: measure whether reduced interaction burden outweighs false spawn/split and mode contamination.

This should not run before E3 establishes that multiple explicit modes are useful.

### E8 — factor/attribute engine

Learn composable factors only from repeated counterfactual comparisons, visual deltas, and interventions that identify contributions.

Purpose: test the actual Concept Shelf hypothesis.

This is not a renamed taste-family engine. Its data model, evidence requirements, UI, and renderer transport differ.

## Projection/data-model variants

The raw observation envelope remains stable, while each engine may own one of these data models.

### D0 — action-choice history

```text
exact action slates
controlled prompt/seed/noise context
winner/anchor
explicit mode assignment
```

Compatible with E1–E4. Cannot justify cross-scope transfer or visual attributes.

### D1 — visual comparative history

```text
image embeddings/features
anchor/candidate visual differences
choice and context
artifact/duplicate annotations
```

Compatible with E5 and parts of E6/E8. Requires a versioned visual encoder and feature receipts.

### D2 — joint action/visual transitions

```text
action delta
visual delta
seed/noise relationship
prompt/control scope
choice
```

Compatible with E6 and causal concept experiments. It distinguishes a visual preference from its model-specific transport head.

### D3 — sequence/context history

```text
ordered preferred media
session/project context
mode labels or responsibilities
time and command intent
```

Compatible with a learned preference prior or drift model after enough user histories exist.

### D4 — factor evidence

```text
counterfactual pairs/slates
attribute query or annotation
localized masks or regions when relevant
visual-delta consistency
composition/preservation outcome
```

Required before an attribute engine can claim extraction or composability.

## UI variants

### U0 — Truthful Current-Image Chooser

```text
choose exact rendered candidate
None of these
More variety
history
```

Use as the common UI for engine comparisons. It minimizes UI semantics while preserving the anchor choice.

### U1 — Explicit Taste Shelf

```text
current active taste
switch
start new taste here
provisional/established status
exemplars
branch/taste fork distinction
```

Compatible with explicit family engines such as E3/E4. Tests whether users understand and benefit from mode ownership.

### U2 — Implicit Taste Suggestions

The system suggests “this may be another taste” after sustained predictive evidence; the user confirms, rejects, or reassigns.

Compatible only with an engine that produces versioned structural-suggestion receipts. It must expose uncertainty and never silently split named modes.

### U3 — Visual Exemplar Browser

Displays persistent preferred-image neighborhoods and retrieves or conditions from exemplars. It does not show action axes as concepts.

Compatible with E5/E6.

### U4 — Counterfactual Concept Lab

Shows controlled pairs/sweeps and asks which recurring property matters. Mature factors can later enter a composition tray.

Compatible with E8 only after factor evidence gates pass. The current singleton-delta Concept Shelf is not this treatment.

### U5 — True Evolution Studio

Displays parent preservation, edit strength, and generative lineage. It requires a parent-conditioned renderer treatment; changing only the UI is invalid.

## Compatibility rules

| UI | Minimum compatible engine/data | Invalid pairing |
|---|---|---|
| U0 chooser | any choice-capable engine | none, if commands stay truthful |
| U1 Taste Shelf | explicit multi-component projection | K=1 engine presented as learned family |
| U2 suggestions | structural predictive receipts | heuristic one-click spawning |
| U3 exemplar browser | visual-exemplar projection | action centroid shown as visual memory |
| U4 concept lab | identified factor evidence + visual transport | taste modes renamed attributes |
| U5 evolution studio | parent-conditioned renderer state | fixed-seed text-to-image navigation called inheritance |

A UI may be switched over the same live session only when it preserves command semantics and consumes the same assigned engine projection. If a UI changes observation meaning, engine ownership, noise policy, or lifecycle rules, switching starts a new treatment branch/session.

## The initial experiment matrix

Do not run the full Cartesian product. Begin with a small staged matrix in which each comparison has one interpretable difference.

| Treatment | Engine | Structure | Planner | UI | Purpose |
|---|---|---|---|---|---|
| T0 | E0 no learner | none | random/local | U0 | exploration floor |
| T1 | E1 legacy 44D | K=1 | current roles, corrected semantics | U0 | preserved baseline |
| T2 | E2 ideal point | K=1 | same candidate pool/roles as T1 | U0 | learner-form ablation |
| T3 | E2 ideal point | K=1 | target + uncertainty/Fisher | U0 | planner ablation |
| T4 | E3 explicit family | user Switch/Spawn | same as T3 | U0 plus minimal mode selector | family-state ablation |
| T5 | E3 explicit family | same as T4 | same as T4 | U1 Taste Shelf | UI ablation |
| T6 | E3 explicit family | suggestion receipts, confirmation | same as T4 | U2 | explicit versus assisted structure |

Only after these gates:

| Treatment | Engine/data | Purpose |
|---|---|---|
| T7 | E4 GP over D0 | nonlinear utility ablation |
| T8 | E5 over D1 | visual memory without action transfer |
| T9 | E6 over D2 | visual preference plus controllable transport |
| T10 | E8 over D4 + U4 | actual composable-factor hypothesis |
| T11 | parent-conditioned renderer + U5 | true evolution hypothesis |

## Factorial and fractional-factorial logic

The equation:

\[
\text{outcome}
=
\text{engine}
+\text{planner}
+\text{UI}
+\text{renderer/noise}
+\text{interactions}
\]

is a reminder that a monolithic A/B result does not identify the cause.

Use staged or fractional-factorial designs:

1. hold UI, renderer, candidate pool, and commands fixed while scoring learners;
2. hold the winning learner and renderer fixed while testing planner policies;
3. hold engine and planner fixed while testing U0 versus U1;
4. test explicit versus suggested structure only after family usefulness passes;
5. test renderer/UI interactions separately for true evolution.

Do not estimate every high-order interaction at once. Promote an interaction only when product observations or earlier data motivate it.

## Offline, shadow, and live comparisons

### Offline replay

Every compatible engine consumes the same chronological events and emits its prediction **before** observing each outcome.

Valid metrics:

- prequential log loss;
- Brier score where defined;
- calibration;
- posterior-predictive entropy;
- computation and state size;
- replay determinism;
- synthetic target recovery.

This compares models on identical slates. It does not show what would have happened if each model had selected different slates.

### Read-only shadow mode

During a live session:

```text
assigned engine
    predicts → plans → owns displayed taste state

shadow engines
    predict before outcome → update namespaced projection after outcome
    never plan, alter UI state, or emit lifecycle commands
```

Shadow projections must be invisible to the user and carry a source-event digest. This avoids the three-authorities problem while collecting comparable evidence.

### Live adaptive evaluation

Once planners diverge, future data is policy-dependent. Compare time-to-design, acceptance rate, and creative usefulness only with randomized or counterbalanced live treatment assignment and matched generation budgets.

The preferred randomization unit is normally a fresh session/task, not a mid-session toggle. Persistent taste and inspiration create carryover. If the same user sees multiple treatments:

- counterbalance treatment order;
- use matched but distinct prompts/tasks;
- start from isolated projection heads;
- record prior exposure;
- analyze user as a repeated-measures factor.

## Ablation metrics

### Learner quality

- same-slate prequential log loss;
- calibration/reliability;
- recovery after an inconsistent vote;
- uncertainty contraction only in observed directions;
- predictive performance per parameter and per vote.

### Search/product quality

- choices and wall time to accepted/exported design;
- first useful candidate latency;
- rate of `NoneOfThese` versus neutral `MoreVariety`;
- perceptual slate diversity and duplicate rate;
- recovery from a poor branch;
- user-rated result quality at a fixed generation budget.

### Family/structure quality

- mode contamination under explicit instructed goals;
- false and missed spawn/split suggestions;
- switch recovery latency;
- evidence per established mode;
- merge/split correction rate;
- user comprehension of Taste Fork versus Branch Fork.

### UI quality

- command-semantics comprehension;
- accidental negative evidence;
- task completion and decision time;
- mode-selection burden;
- perceived control and predictability;
- whether the user can explain what will happen before clicking.

### Representation/transport quality

- control responsiveness and conditioning;
- cross-seed and cross-prompt transfer by separate condition;
- visual preference prediction;
- transport success from taste representation to generated output;
- concept preservation and off-target change where applicable.

## Data and storage design

Recommended logical namespaces:

```text
interaction_events
    one factual append-only stream

treatment_assignments
    user/session/task → pinned treatment_id

engine_projections
    treatment_id + engine_revision + projection_schema + cursor

predictive_receipts
    before-event probabilities and approximation revision

planner_receipts
    candidate pool, acquisition terms, selected slate

ui_telemetry
    exposure, position, preview, command timing

artifacts/features
    immutable render and representation provenance
```

Never place two engines' fields into one catch-all taste JSON object. Namespaced discriminated projections make incompatibility explicit.

If a new engine needs a genuinely new fact—for example an attribute mask—add a versioned event extension. Do not infer it later from UI telemetry and call it ground truth.

## Treatment isolation rules

1. A session/task pins one authoritative `treatment_id` before the first proposal.
2. Only that treatment's engine projection may steer candidates or appear as learned state.
3. Shadow projections are read-only with respect to product behavior.
4. Changing engine, observation semantics, or renderer/noise policy creates a new treatment head.
5. Raw events may be replayed only by engines whose qualification rules accept their contexts.
6. A treatment-specific event extension is never silently dropped and reinterpreted as a common fact.
7. UI routes with identical commands may share an engine; routes with different command meanings may not share a mutable projection.
8. Every metric receipt names the treatment, engine, planner, UI, renderer, and event cursor.
9. No treatment imports derived atlas, concept, or competing-engine state as if it were raw evidence.
10. Production has one promoted treatment; the harness may retain many historical/shadow projections.

## What “different data models” should mean

It should mean different explicit hypotheses about sufficient state, such as:

```text
actions are sufficient
visual exemplars are sufficient
actions + visual deltas are sufficient
ordered media history is necessary
counterfactual factor evidence is necessary
```

It should not mean four undocumented JSON shapes that all receive the same name `taste`.

Each data-model treatment must answer:

- What observations identify its parameters?
- What does it predict before seeing the vote?
- How does it generate or rank a new image?
- Which contexts can it transfer across?
- What state can the user inspect or correct?
- What falsifiable result would retire it?

## First implementation slice

The first harness PR should add:

1. a pinned `TreatmentAssignment` contract;
2. a `TasteEngine` protocol;
3. namespaced projection storage;
4. before-outcome predictive receipts;
5. E1 legacy and E2 ideal-point adapters;
6. one assigned engine plus one or more read-only shadow engines;
7. U0 as the common UI;
8. tests proving shadows cannot affect planning, session snapshots, or commands.

Then run T1 versus T2 on identical logged slates. Only after that receipt should the project add E3 and U1.

## Final principle

The research platform should be plural; each experiment should be singular.

```text
many candidate engines and UIs in the repository
        ↓ pinned treatment assignment
exactly one preference authority in a live session
        ↓ immutable common facts
fair replay, shadow comparison, and staged ablation
```

That gives Art Optimizer room to discover that the ideal-point family is wrong without returning to three simultaneous, contradictory definitions of the same user's taste.
