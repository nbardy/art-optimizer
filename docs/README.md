# Documentation Map

This directory contains architecture and implementation documents. The `reviews/` directory contains source-backed analysis and postmortems. The `experiments/` directory contains executable hypotheses, configurations, and result receipts.

## Status vocabulary

Every substantial document should declare one of these statuses near the top:

- **Normative current:** governs current code or a currently scheduled implementation.
- **Implemented baseline:** accurately describes T0 but is not automatically the future product contract.
- **Research proposal:** a hypothesis awaiting implementation or evidence.
- **Historical:** retained for provenance; superseded for future design.
- **Source note:** raw observation or external review, preserved without silently rewriting it.

## Authority order

When documents conflict, use this order:

1. current executable code and tests;
2. [`ROADMAP.md`](../ROADMAP.md) and an active experiment policy;
3. normative current contracts in `docs/`;
4. implemented-baseline specifications;
5. research proposals and reviews;
6. historical documents and source notes.

A review can identify a flaw in a normative document, but it does not silently change runtime behavior. A code PR should update the affected contract and experiment receipt together.

## Current map

### Architecture and code

| Document | Status | Purpose |
|---|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | implemented baseline | system components and data flow |
| [`CODE_DESIGN.md`](CODE_DESIGN.md) | implemented baseline | code boundaries and typed contracts |
| [`STATE_AND_CONTROL_CONTRACT.md`](STATE_AND_CONTROL_CONTRACT.md) | implemented baseline | identity, replay, worlds, designs, branches, actions |
| [`MODEL_CODECS.md`](MODEL_CODECS.md) | normative current | model/codec boundary and local model support |
| [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) | current snapshot | what is implemented and what remains empirical |

### T0 interaction and algorithms

These describe the controlled-search baseline. They must remain executable for comparison, but they are not assumed to be the Round 2 product contract.

| Document | Status | Purpose |
|---|---|---|
| [`INTERACTION_MODEL_V0.md`](INTERACTION_MODEL_V0.md) | implemented baseline | original preview/commit/reroll/favorite/history semantics |
| [`V0_ALGORITHM_SPEC.md`](V0_ALGORITHM_SPEC.md) | implemented baseline | original Bayesian choice model and planner |
| [`UI_DESIGN.md`](UI_DESIGN.md) | implemented baseline / historical product framing | original one-canvas interaction |
| [`PERSISTENT_PREFERENCE_ATLAS.md`](PERSISTENT_PREFERENCE_ATLAS.md) | research baseline | persistent preference representation |

### Readiness and experiments

| Document | Status | Purpose |
|---|---|---|
| [`CONTROL_BASIS_EXPERIMENT.md`](CONTROL_BASIS_EXPERIMENT.md) | research proposal; still required | validates whether model controls produce useful visual movement |
| [`IMPLEMENTATION_READINESS.md`](IMPLEMENTATION_READINESS.md) | historical readiness record | records the assumptions used before the first real session |
| [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) | historical synthesis | early research notes superseded in part by `reviews/` |

## Other documentation roots

- [`../reviews/README.md`](../reviews/README.md): prior work, claim maps, design reviews, Round 1 source notes, and root-cause analysis.
- [`../experiments/README.md`](../experiments/README.md): experiment directory contract and reproducibility rules.
- [`../experiments/round2/README.md`](../experiments/round2/README.md): current experiment queue.
- [`../ROADMAP.md`](../ROADMAP.md): product fork, sequencing, and promotion gates.

## Documentation rules

1. Do not describe a proxy as a learned visual concept unless pixels or visual representations participate in the evidence.
2. Do not call navigation ancestry generative inheritance.
3. Do not call a layout variant an algorithm experiment unless its policy bundle differs.
4. Keep raw source notes intact and place interpretation in a separate review.
5. Every experiment document should identify baseline, intervention, metrics, failure modes, and non-claims.
6. Prefer links to exact modules and event types over duplicated prose.
7. Avoid giant renames solely for aesthetics; reorganize code when an actual boundary changes.
