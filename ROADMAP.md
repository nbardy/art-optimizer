# Art Optimizer Roadmap

**Status:** Round 1 complete; Round 2 research planning  
**Tracking issue:** [#10 — separate novelty, preference, perceptual diversity, concepts, and true image evolution](https://github.com/nbardy/art-optimizer/issues/10)

## Current truth

Art Optimizer currently provides a stable research scaffold for interactive search over a bounded, prompt-conditioned control chart. It has working local model loading, streaming candidates, branch history, replay metadata, exposure-aware discrete choice, and modular renderer/codec/planner boundaries.

Round 1 also falsified the stronger product interpretation. The current baseline does **not** yet demonstrate:

- parent-conditioned image evolution;
- perceptually diverse candidate slates;
- validated semantic controls;
- recurring visual-concept discovery;
- materially different UI/algorithm treatments.

The repository should preserve the current implementation as **Baseline T0: controlled generative-space search** while Round 2 develops and compares divergent systems.

## Product question

Round 2 must distinguish three promises rather than making one interface imply all three:

### A. Open-ended generative search

Find surprising images and conditioning regions that are difficult to express as prompts. Relevant methods include calibrated authored controls, random soft-embedding subspaces, stochastic-root exploration, perceptual slate diversity, and truthful preference commands.

### B. True image evolution

Selecting an image should make it a generative parent whose subject, structure, or details can survive into descendants. This requires parent-conditioned rendering, latent/inversion/reference state, preservation controls, and separate navigation versus generative ancestry.

### C. Reusable visual concepts

Recurring visual properties should be inferred from repeated visual and generative evidence, promoted provisionally, tested across roots/contexts, and made composable only after held-out success.

The recommended initial priority is **A**, followed by a focused comparison with **B**. **C** should begin only after meaningful visual embeddings and repeated evidence exist.

## Round 2 sequence

### Phase 0 — correctness and semantics

Before changing the optimizer:

1. split neutral `More variety` from preference-bearing `None of these`;
2. add `Broken / not judgeable` with zero aesthetic effect;
3. fix branch-checkpoint persistence after non-navigation learner updates;
4. replace cancellable wrapper tasks with an explicit render-job queue;
5. make command receipt, session projection, and evidence updates crash-consistent;
6. add artifact retention and cleanup policies;
7. scope concrete conditioning bases by prompt/model/configuration instance;
8. call the event log an audit log unless state can be reconstructed from it.

**Gate:** a user can correctly predict what each visible command trains, and restart/retry behavior is deterministic.

### Phase 1 — representation tests before product tests

1. run fixed-seed sweeps over every authored axis;
2. test multiple prompts, seeds, amounts, and embedding strengths;
3. measure output effect size, monotonicity, redundancy, artifacts, and off-target drift;
4. estimate the local action-to-image geometry;
5. compare authored axes with random and prompt-manifold soft directions;
6. create prompt-specific control-basis instance IDs.

**Gate:** a coordinate enters an interactive policy only when it produces reliable visible movement within a declared validity region.

### Phase 2 — truthful search treatments

Build a coherent **Truthful Search Canvas** treatment:

- `Choose` updates preference;
- `More variety` changes novelty/noise policy without a preference label;
- `None of these` records a weak anchor-wins observation;
- `Broken` excludes a render without an aesthetic label;
- a hybrid slate mixes same-root, correlated-root, and fresh-root candidates;
- output diversity is measured in image space;
- an eight-parameter preferred-target learner is the simple baseline against the current 44-parameter quadratic learner.

**Gate:** slates are perceptually more diverse than T0, command comprehension is high, and time-to-first-liked candidate improves.

### Phase 3 — random soft-direction explorer

Optimize inside small, calibrated random subspaces of the model conditioning representation. Retain successful directions and refresh unsuccessful ones. See [`experiments/round2/RANDOM_SOFT_DIRECTIONS.md`](experiments/round2/RANDOM_SOFT_DIRECTIONS.md).

**Gate:** the treatment discovers useful, repeatable visual movement beyond authored prompt axes without excessive broken or inert directions.

### Phase 4 — true evolution treatment

Add one explicit parent-conditioned renderer mode and preserve the existing search renderer as a separate treatment.

**Gate:** independent judges can reliably identify descendants as inheriting selected parent qualities, with controlled off-target drift.

### Phase 5 — provisional concept learning

Create server-side `ConceptObservation` facts containing action delta, visual delta, context, stochastic relation, and outcome. Concepts remain provisional until repeated, cross-context evidence and held-out recasts support them.

**Gate:** concepts merge into fewer, stronger components; exemplars share a recognizable property; and recast preserves that property across fresh roots.

## Planned implementation PRs

| PR | Scope | Depends on |
|---|---|---|
| R2.0 | command semantics, checkpoint/state fixes, render queue, retention | current `main` |
| R2.1 | representation benchmark harness and basis-instance identity | R2.0 |
| R2.2 | hybrid noise slate, perceptual features, simple target learner | R2.1 |
| R2.3 | random soft-direction treatment | R2.1–R2.2 |
| R2.4 | parent-conditioned evolution treatment | R2.0 |
| R2.5 | provisional visual/action concept evidence and Concept Garden | R2.2 or R2.3 |
| R2.6 | policy-level experiment harness and comparative study | all promoted treatments |

Avoid combining these into one giant rewrite. Each PR must preserve T0 as an executable baseline and include a treatment-specific receipt.

## Decision gates

A feature should not be promoted because it looks impressive in one session. Promotion requires:

- an explicit hypothesis;
- a baseline and ablation;
- complete model, seed, basis, and policy provenance;
- quantitative output metrics where meaningful;
- human judgments for perceptual and semantic claims;
- failure cases;
- a clear statement of what the experiment did **not** establish.

## Required user decisions

The remaining product questions are tracked in [`experiments/round2/DECISIONS_NEEDED.md`](experiments/round2/DECISIONS_NEEDED.md). They concern the primary promise, concept ontology, acceptable interaction burden, desired wildness, and transfer scope.

## Reading order

1. [`README.md`](README.md) — run the current baseline.
2. [`docs/README.md`](docs/README.md) — understand documentation status.
3. [`reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md`](reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md) — Round 1 diagnosis.
4. [`reviews/12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md`](reviews/12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md) — narrow technical interventions.
5. [`reviews/13_TEN_IDEALS_AND_DIVERGENT_PRODUCT_DESIGNS.md`](reviews/13_TEN_IDEALS_AND_DIVERGENT_PRODUCT_DESIGNS.md) — divergent product space.
6. [`experiments/round2/README.md`](experiments/round2/README.md) — executable Round 2 plan.
