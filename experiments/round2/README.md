# Round 2 Experiment Plan

**Status:** planned  
**Umbrella issue:** [#10](https://github.com/nbardy/art-optimizer/issues/10)  
**Baseline:** current `main`, named **T0 Controlled Search**

## Objective

Round 2 should determine which representations and product contracts produce useful creative behavior. It should not add another surface-level interface over the same eight authored coordinates.

The objects under test are separate:

```text
comparison anchor
proposal center
generative parent
stochastic root
preference posterior
provisional move
visual concept
persistent taste mode
experiment policy
```

## T0 — controlled-search baseline

T0 retains:

- one prompt-conditioned eight-dimensional authored chart;
- one world seed;
- absolute actions;
- four role-balanced candidates;
- multinomial outside-option preference updates;
- branch/history/replay infrastructure.

T0 is useful for controlled comparisons. It must be relabeled honestly and should not provide evidence for parent-evolution or visual-concept claims.

## Experiment queue

### E0 — semantic and state correctness

Split visible commands and fix state defects before research conclusions:

```text
Choose
More variety        no preference update
None of these       weak anchor-wins update
Broken              zero aesthetic update
```

Also address branch checkpoint mutation, stale render jobs, transaction/receipt recovery, retention, and basis-instance scope.

### E1 — authored-basis calibration

For each model/prompt/seed:

- render signed amount sweeps for every axis;
- test embedding strengths;
- measure visual effect, monotonicity, artifacts, redundancy, and off-target drift;
- estimate local pullback geometry;
- remove or condition axes that do not pass.

### E2 — hybrid stochastic slate

Compare same-root control with correlated/fresh-root novelty. Candidate-level provenance declares the noise relationship. Test both mixed exploratory slates and crossed 2×2 action/root questions.

### E3 — perceptual slate selection

Select candidates using actual or predicted image representations and a diversity objective such as DPP/log-determinant rather than Euclidean action distance alone.

### E4 — simple preferred-target learner

Compare the current 44-parameter quadratic utility model against an eight-parameter preferred-target model:

\[
u(a\mid\theta)=-\frac12(a-\theta)^TQ(a-\theta).
\]

Evaluate cold-start regret, calibration, order sensitivity, and time-to-first-liked candidate.

### E5 — random soft-direction explorer

Search calibrated low-dimensional random subspaces in prompt-conditioning space, including language-manifold and residual directions. See [`RANDOM_SOFT_DIRECTIONS.md`](RANDOM_SOFT_DIRECTIONS.md).

### E6 — true parent-conditioned evolution

Add a renderer treatment that consumes parent image/latent/reference state and exposes preservation strength. Maintain navigation parent and generative parent as separate fields.

### E7 — provisional visual concepts

Persist observations containing action delta, visual delta, context, seed relation, and outcome. Use a provisional lifecycle and require repeated support across anchors/roots before composition.

### E8 — coherent product treatments

Compare at least three complete policy bundles:

| Treatment | Promise | Renderer | Novelty | Learning |
|---|---|---|---|---|
| T1 Truthful Search | navigate a generative space | absolute search | hybrid roots | simple preference target |
| T2 Random Soft Search | discover non-promptable regions | random conditioning subspace | basis refresh + roots | preference over subspace |
| T3 Evolution Studio | evolve a selected image | parent conditioned | mutation strength | preference + preservation |
| T4 Concept Garden | learn recurring reusable properties | promoted concept transport | context dependent | provisional visual/action mixture |

Do not switch between treatments while silently reusing incompatible posteriors or concept projections.

## Five mathematical partial solutions

The formal derivations and limitations are in [`../../reviews/12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md`](../../reviews/12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md):

1. perceptual pullback metric and output-diverse slate selection;
2. two-factor seed/control design;
3. Bayesian directional mixture for provisional concepts;
4. typed command-intent likelihood;
5. parent-conditioned transport.

These are partial solutions for separate failures, not a single architecture mandate.

## Shared instrumentation

Every candidate should eventually record:

```text
policy_id
renderer_mode
model and revision
control_basis_family and instance
representation_revision
anchor and proposal-center IDs
generative_parent_id
seed/noise ID and relation
action/control state
visual embedding reference
hidden-pool source
selection role
render timing and failures
```

Every command records its visible label and declared preference/novelty effect.

## Promotion order

1. E0 correctness.
2. E1 representation validation.
3. E2/E3 visible candidate diversity.
4. E4 learner comparison.
5. E5 random soft directions.
6. E6 true evolution.
7. E7 concepts.
8. E8 comparative product study.

Concept UI work should not lead this sequence; it depends on evidence produced by earlier phases.

## Human input required

See [`DECISIONS_NEEDED.md`](DECISIONS_NEEDED.md). The most important unresolved choice is whether the primary promise is surprising search, true image inheritance, or reusable concept composition.

## Results

Use [`RESULTS_TEMPLATE.md`](RESULTS_TEMPLATE.md) for every GPU or user-session receipt.
