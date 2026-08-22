# Repository Structure and Evolution Plan

**Status:** normative organization plan; staged code migration

The repository should make it obvious whether a file is executable code, a governing contract, a research interpretation, raw evidence, or an experiment receipt. Round 1 accumulated all five, but the top-level hierarchy did not distinguish them strongly enough.

## Current top-level contract

```text
art-optimizer/
├── art_optimizer/          executable application and shared runtime modules
├── tests/                  deterministic unit/integration/browser contract tests
├── scripts/                operational and benchmark entry points
├── docs/                   architecture and implementation contracts
├── reviews/                prior work, design reviews, postmortems, source notes
├── experiments/            hypotheses, configurations, scripts, and result receipts
├── ROADMAP.md              current sequence and promotion gates
├── README.md               honest product status and run instructions
└── CONTRIBUTING.md         contribution workflow
```

## Documentation ownership

### `docs/`

Use for contracts that implementation PRs are expected to obey:

- state identity and replay;
- service/module boundaries;
- API/event contracts;
- renderer/codec interfaces;
- active algorithm specifications;
- implementation status.

A document describing only a past hypothesis should be marked historical rather than quietly governing new work.

### `reviews/`

Use for interpretation rather than runtime authority:

- literature reviews;
- claim/citation maps;
- design audits;
- postmortems;
- divergent design explorations;
- raw notes under `reviews/source_notes/`.

Raw feedback is preserved separately from the project’s interpretation of it.

### `experiments/`

Use for executable research claims:

```text
experiments/<round-or-topic>/
├── README.md               hypothesis, treatments, gates
├── configs/                checked-in non-secret configurations
├── scripts/                experiment-specific runners/analysis
├── fixtures/               small deterministic test inputs
└── results/                compact receipts, summaries, plots, no large checkpoints
```

Generated images, checkpoints, and large embeddings should live outside Git and be referenced by digest/location in a result receipt.

## Code-boundary target

The current package is intentionally small. Do not perform a large mechanical move now. As Round 2 changes actual behavior, migrate toward these boundaries:

```text
art_optimizer/
├── app.py                  HTTP/SSE composition only
├── domain.py               immutable shared fact and state types
├── service.py              authoritative command/state transitions
├── policies/               complete experiment policy bundles
│   ├── base.py
│   ├── controlled_search.py
│   ├── random_soft_search.py
│   └── evolution.py
├── representations/        authored, random, visual, and concept representations
│   ├── control_basis.py
│   ├── visual_features.py
│   └── concepts.py
├── renderers/              search/edit renderer implementations
├── learners/               preference and concept learners
├── planning/               candidate-pool and slate-selection policies
├── storage/                audit facts, projections, artifacts, retention
└── web/                    shared client transport plus treatment-specific views
```

### Migration rule

Move a module only when the PR introduces or changes that boundary. Do not create empty abstraction directories or duplicate compatibility layers merely to match the target tree.

## Experiment policy as the unit of divergence

A treatment should resolve to one immutable policy declaration:

```text
ExperimentPolicy
    policy_id
    renderer_mode
    representation_id
    candidate_count
    candidate_generation_policy
    noise_policy
    command_semantics
    preference_learner_id
    concept_learner_id
    concept_visibility/editability
    projection_schema
    metric_set
```

Two interfaces that share all of these fields are presentation variants, not independent algorithm experiments.

## Data layers

Keep four layers distinct:

### 1. Immutable facts

What happened:

```text
UserCommand
CandidateGenerated
CandidateExposed
ChoiceObserved
RenderFailed
FavoriteChanged
ConceptObservation
```

### 2. Generated artifacts

Images, embeddings, latent/inversion state, manifests, and parent/noise provenance.

### 3. Derived projections

Session state, history views, concept components, preference posteriors, and UI-specific projections. A projection declares the policy/revision that produced it.

### 4. Experiment receipts

Configuration, commit, hardware, model revision, metrics, plots, human annotations, failure cases, and conclusions.

Do not call the system event sourced until authoritative projections can be reconstructed from immutable facts.

## Scope identifiers

Round 2 requires scope at multiple levels:

```text
model_family
model_revision
control_basis_family
control_basis_instance
prompt/world context
renderer mode
experiment policy
representation revision
visual-feature revision
```

A model-level basis family is not enough to justify transferring concrete prompt-conditioned numeric actions between prompts.

## Retention

- source notes and compact receipts: retain indefinitely;
- session facts and manifests: retain according to experiment policy;
- candidate PNGs and low-resolution probe pools: configurable TTL and favorite/export exemptions;
- model weights: Hugging Face cache, never committed;
- visual embeddings: external artifact store or compact local cache, addressed by digest.

## Pull-request discipline

A research implementation PR should include:

1. one treatment or narrow infrastructure change;
2. updated domain/event contracts;
3. tests for command semantics and state recovery;
4. an experiment README/config;
5. a result receipt or explicit statement that the PR adds infrastructure only;
6. updated status/non-claim language.

The current T0 treatment remains runnable until a replacement has evidence and a migration decision.
