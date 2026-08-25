# Track MM-2 — Model Families, Mathematical Interfaces, and Research Handoff

## Executive finding

The current mathematical code is too tightly coupled to one representation and one inference routine to serve as a clean research platform. The class surface is small, but the objects returned by it are implementation arrays rather than durable mathematical contracts.

The clean handoff is to define **model policy**, **posterior state**, **prediction**, **assignment**, **comparison**, and **acquisition** as separate interfaces. That allows a mathematician to return a finite-mixture ideal-point model, a sticky HMM, a GP mixture, or a calibrated geometry without touching UI/event logic.

## 1. Current coupling

[`EmergentTasteEngine`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py) currently owns:

- event validation;
- fitting all values of `K`;
- mixture/HMM inference;
- ideal-point optimization;
- model selection;
- predictive probability;
- hard display assignment;
- exemplar selection;
- taste labels and status;
- public API serialization.

This makes a mathematical change also a UI/projection change.

`TasteFit` exposes:

```python
centers
weights
responsibilities
filtered_state
effective_counts
log_likelihood
```

but lacks:

- covariance/uncertainty;
- transition posterior counts;
- convergence diagnostics;
- objective decomposition;
- component revision/lineage;
- model-policy digest;
- full predictive distribution;
- numerical tolerance receipt.

## 2. Proposed mathematical contracts

### Model policy

```python
@dataclass(frozen=True)
class TasteModelPolicy:
    utility_family: UtilityFamily
    latent_process: LatentProcessPolicy
    prior: TastePrior
    choice_temperature: float
    observation_weight_policy: str
    inference: InferencePolicy
    model_selection: ModelSelectionPolicy
    geometry: ActionGeometry
    revision: str
```

No value should be an undocumented constructor default.

### Observation

```python
@dataclass(frozen=True)
class ChoiceObservation:
    observation_id: str
    scope: RepresentationScope
    slate: ChoiceSlate
    outcome: AlternativeId
    observation_weight: float
    display_receipt: DisplayReceipt
    created_at: datetime
```

Prediction receipts belong beside, not inside, the observation fact:

```python
PrequentialPrediction(
    observation_id,
    model_revision,
    full_probabilities,
    state_prior,
    numerical_receipt,
)
```

This avoids retroactively constructing a fact that claims to contain a prediction generated before itself.

### Posterior

```python
@dataclass(frozen=True)
class TastePosterior:
    components: tuple[TasteComponentPosterior, ...]
    latent_state_posterior: LatentStatePosterior
    evidence_ids: tuple[str, ...]
    policy_digest: str
    scope_digest: str
    convergence: ConvergenceReceipt
    revision_id: str
```

### Component posterior

For the ideal-point baseline:

```python
TasteComponentPosterior(
    component_id,
    mean_theta,
    covariance_theta,
    prevalence_posterior,
    effective_evidence,
    parent_component_ids,
)
```

### Prediction

```python
predict(
    posterior: TastePosterior,
    slate: ChoiceSlate,
    context: PredictionContext,
) -> CategoricalPrediction
```

Return the full vector, not only the probability of the eventual winner.

### Assignment

```python
assign(
    posterior,
    observations,
) -> ResponsibilityMatrix
```

Hard UI labels are a projection of this matrix and should not feed back into the model.

### Model comparison

```python
compare(
    candidates: Sequence[ModelPredictionStream],
    policy: ModelSelectionPolicy,
) -> ModelComparisonReceipt
```

The receipt should show:

- cumulative and windowed prequential scores;
- complexity term and why it applies;
- eligibility gates;
- uncertainty/sensitivity;
- selected model;
- simpler models within tolerance.

### Acquisition

```python
propose(
    posterior,
    current_action,
    valid_domain,
    render_budget,
    acquisition_policy,
) -> SlateProposal
```

The proposal must include the acquisition score decomposition and random seed. It is separate from the model fit.

## 3. Model-family ladder

A disciplined research plan should compare models in increasing complexity.

### M0 — no-learning/random baseline

Uniform choice prediction and fixed action proposals. Necessary to quantify whether any learner helps.

### M1 — single ideal point

\[
u(a)=-\frac12(a-\theta)^TQ(a-\theta).
\]

Use calibrated fixed `Q` and posterior uncertainty.

### M2 — finite exchangeable mixture

Multiple ideal points with no temporal persistence. This tests whether multiple modes are needed before adding sequence assumptions.

### M3 — sticky finite HMM

Current conceptual model, with mathematically correct transition inference and explicit branch/task adjacency.

### M4 — flexible local utility

GP or spline utility inside one/multiple modes. Only after representation validation and enough data.

### M5 — image/action joint model

Adds visual observations or multimodal preference features. This is required before claiming tastes are extracted from sets of images rather than action choices.

The system should not jump from M1 to M5 because M3 sounds more psychologically natural. Each step needs a predictive gain.

## 4. Geometry must be an object

Current utility uses Euclidean distance in authored action coordinates. Replace implicit identity geometry with:

```python
class ActionGeometry(Protocol):
    def squared_distance(self, a, b, context) -> float: ...
    def project(self, a, context) -> Action: ...
    def tangent_basis(self, a, context) -> Matrix: ...
    def digest(self) -> str: ...
```

Candidate implementations:

- identity metric;
- diagonal effect-size calibration;
- local pullback metric `JᵀWJ`;
- learned positive-definite metric;
- context-specific whitening of a direction bank.

Then the ideal-point model becomes:

\[
u_k(a)=-\frac12 d_c(a,\theta_k)^2
\]

without hard-coding `Q=I`.

## 5. Temporal adjacency must be declared

The sticky HMM assumes event `t-1` is the predecessor of event `t`. In an interactive branch system, chronology may include:

- continued exploration on one branch;
- restore to an old branch;
- a new world;
- gallery-created fresh session;
- task/prompt change;
- long pause.

Define a transition context:

```python
TransitionContext(
    same_branch,
    same_world,
    elapsed_time,
    explicit_switch,
    restore_kind,
)
```

Then either:

- reset latent-state prior at declared boundaries;
- use context-dependent transition matrices;
- or model each branch sequence separately.

Without this, stickiness may cluster navigation history rather than taste.

## 6. Reproducible numerical policy

Every fit should return:

```text
optimizer
initialization seeds
number of starts
iteration cap
absolute/relative tolerances
objective history
convergence reason
minimum Hessian eigenvalue
jitter used
posterior approximation
QMC method/sample count/seed
```

Current code hides most of these in implementation constants.

## 7. Mathematical acceptance tests

A model implementation should not be accepted only because synthetic blocks produce expected component counts. Require:

### Exact small problems

- enumerate hidden-state paths and compare HMM likelihood/posteriors;
- finite-difference gradients and Hessians;
- compare optimizer solution with high-precision reference;
- permutation invariance/equivariance tests.

### Simulation recovery

Simulate from known parameters across:

- one and multiple tastes;
- weak/strong separation;
- varying slate geometry;
- noisy choices;
- branch resets;
- unequal prevalence;
- different persistence.

Measure parameter recovery, predictive calibration, and false split/merge rates.

### Robustness

- initialization sensitivity;
- coordinate rescaling;
- missing/invalid events must fail, not silently fall back;
- long sequences;
- nearly identical alternatives;
- saturated logits;
- under-supported components.

### Product validity

- model predicts actual user choices better than M0/M1;
- discovered components remain useful in held-out galleries/tasks;
- labels/components are stable enough for users to recognize;
- gains survive matched generation budgets.

## 8. Deliverable for a mathematician

A useful brief should contain:

1. formal objects from `01_formal_problem_landscape.md`;
2. a frozen dataset schema of qualified choice observations;
3. a baseline implementation with exact numerical tests;
4. an evaluation harness producing prequential and calibration metrics;
5. explicit model families M0–M5;
6. product constraints: fixed-root ordinary loop, no hybrid-root likelihood, gallery is non-preference;
7. acceptable runtime budget;
8. required output interfaces above.

The requested output should be a package of mathematical functions and proofs/invariants, not a UI rewrite.

## Verdict

The repository has enough structure to support serious mathematical work, but the current engine class conflates model, inference, selection, and presentation. Split those contracts before asking a mathematician to improve the algorithm; otherwise every mathematical contribution will arrive entangled with repository-specific state conventions.
