# Track MC-2 — Legacy Learner, Planner, and Embedding-Geometry Correctness

## Executive finding

The legacy branch learner is a competent small sequential Laplace approximation, but its policy is under-specified and order-dependent. The authored embedding directions are a plausible experiment, not a validated coordinate system. The planner then treats those coordinates as Euclidean, equally scaled, and visually meaningful.

The combined system can learn and move, but no mathematical argument currently connects action-space distance to the visual or preference geometry claimed by the product.

## 1. Legacy quadratic learner

[`BayesianChoiceModel`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/preference.py) uses features:

\[
\psi(a)=
[a_1,\ldots,a_d,
 a_1^2,\ldots,a_d^2,
 a_1a_2,\ldots,a_{d-1}a_d].
\]

For \(d=8\), this is 44 parameters. Relative features remove common anchor utility from each slate.

### What is correct

- softmax normalization is numerically stabilized;
- gradient and Fisher/Hessian structure are appropriate for multinomial logistic utility;
- covariance is symmetrized and eigenvalue-stabilized;
- the anchor is represented as zero relative utility;
- exposure masking is incorporated into the choice set.

### What is not a coherent Bayesian history model

Every observation treats the previous Laplace posterior as a new Gaussian prior, after inflating covariance by a forgetting factor. This is sequential assumed-density filtering, not joint MAP or exact Bayesian updating.

Consequences:

- order matters;
- posterior approximation error compounds;
- undo/reassignment cannot be exact without replay;
- `forgetting_factor` simultaneously encodes drift and uncertainty inflation;
- historical interpretation is unclear.

If T0 is only a baseline, this is acceptable. If it is used as an experimental control, its exact policy must be versioned and replayed from evidence.

## 2. Learner configuration is missing from snapshots

`GaussianSnapshot` stores mean, covariance, dimensions, and observation count. It does not store:

```text
prior variance
temperature
forgetting factor
optimizer iteration cap
stabilization revision
feature-map revision
```

Restoring a snapshot under changed constructor defaults changes its future semantics without changing its identity.

The snapshot needs a `model_policy_digest`, or the learner state should be reconstructed from observations under a pinned policy.

## 3. Damped Newton line search can accept a worse step

The line search halves while:

```python
scale > 1 / 128 and objective(next_value) < old_objective
```

When `scale` reaches exactly `1/128`, the loop exits even if the candidate still decreases the objective. The code then accepts `next_value` unconditionally.

Fix by:

- explicitly rejecting the step if no improving scale is found;
- or use a trusted convex optimizer with convergence receipt;
- and test objective monotonicity.

## 4. Exposure repair weakens data integrity

If the chosen candidate is not marked exposed, `update_choice` silently appends it to the exposed set. A user cannot choose an unseen candidate through the normal UI, so this state indicates a client/audit inconsistency.

Prefer rejecting the observation or recording a qualification-repair event. Silent repair makes exposure receipts less meaningful.

## 5. Explicit inverses are unnecessary

The learner repeatedly computes matrix inverses for prior precision and posterior covariance. The matrices are small, so this is not a performance crisis, but Cholesky solves are more stable and provide better positive-definiteness diagnostics.

## 6. Authored embedding directions are heuristic tensor differences

[`build_direction_bank`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/embedding_conditioning.py) encodes a base prompt plus positive/negative endpoint prompts and defines:

\[
d_i=\operatorname{RMSMatch}
\left(\frac{e_i^+-e_i^-}{2},e_0\right).
\]

The mixed conditioning is:

\[
e(a)=e_0+
\frac{\lambda}{\sqrt d}
\sum_i a_i d_i.
\]

This is a useful empirical construction, but it has no guarantee of semantic or geometric validity.

### Risks

1. **Token-position subtraction.** Endpoint prompts can tokenize differently. Subtracting sequence tensors position by position is not necessarily a tangent direction for one concept.
2. **Noise amplification.** If an endpoint difference has very small RMS, RMS matching can magnify mostly numerical/linguistic noise. The `1e-6` floor prevents division by zero, not bad directions.
3. **No centering against base.** The positive-negative chord need not pass through or be locally relevant to the base prompt embedding.
4. **No orthogonalization.** Directions can be highly correlated or nearly collinear.
5. **No effect calibration.** Equal action magnitude does not imply equal image change.
6. **Global static basis label.** The actual direction bank is prompt-conditioned, but the basis revision string is model-global.
7. **No validity radius.** Linear mixing can leave the useful conditioning manifold at larger strengths.
8. **No post-mix normalization.** Embedding norm/distribution can drift with combinations.

## 7. Krea mask construction may activate non-base positions

`Krea2ConditioningAdapter.output_mask` computes:

```python
mask.any(dim=0, keepdim=True)
```

across the batch containing the base and every endpoint prompt. The output embedding is the base embedding plus mixed deltas, but the mask is the union of token positions used by any endpoint.

Positions that are padding/inactive for the base may become active. Whether this is correct depends on the pipeline contract; it needs a focused test against expected Krea conditioning behavior rather than an intuitive union.

## 8. The `1/sqrt(d)` scale is not an axis calibration

Dividing by \(\sqrt d\) limits aggregate norm when many independent unit directions are active. But:

- directions are not independent;
- often only one coordinate is active;
- each axis may have a different visual gain;
- model endpoint differences have already been RMS-normalized.

Thus a single-axis maximum is also divided by \(\sqrt8\), potentially making it unnecessarily weak. The scale should be calibrated per direction or through a measured metric, with an aggregate trust-region constraint for combinations.

## 9. Planner geometry is unjustified

[`CandidatePlanner`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/planner.py) uses Euclidean action distance for:

- local radius;
- diversity from selected points;
- bounded surprise;
- target distance.

It mixes several scores with fixed coefficients:

```text
mean utility
posterior standard deviation
Euclidean diversity
Euclidean distance from anchor
atlas target distance
```

These coefficients are hand-tuned and not dimensionless under coordinate rescaling. A change in direction calibration changes planner behavior even when rendered effects are identical.

The planner should consume an `ActionGeometry` object and a versioned acquisition policy.

## 10. “Informative probe” is not expected information

The probe role primarily maximizes posterior utility standard deviation plus action diversity. This can choose saturated comparisons where one alternative is almost certain under posterior samples. High variance in latent utility is not the same as expected entropy reduction or Fisher information in the observed choice.

Call it `uncertainty_probe` unless the acquisition calculation includes choice probabilities and expected posterior change.

## 11. Role-to-slot and visible-label bias

Roles are always created in slots 1–4. The baseline and emergent UIs expose role labels such as local, probe, different, or farther. The preference likelihood has no position or role-label bias term.

A user who prefers a screen corner or is attracted to “surprise” can teach that bias to the action utility. Randomize/counterbalance roles and hide labels outside debug mode, or model the bias explicitly.

## 12. Required representation tests

Before learning tastes over this space, run for every model/prompt family:

1. positive/negative sweep for each direction;
2. effect magnitude versus action strength;
3. monotonicity and sign consistency;
4. repeated seeds at fixed action;
5. direction correlation and condition number;
6. off-target drift and catastrophic subject changes;
7. local Jacobian or finite-difference visual metric;
8. base-mask behavior for Krea;
9. active-axis scaling with and without `1/sqrt(d)`;
10. held-out human usefulness.

A direction that is inert, nonmonotonic, or redundant should not be a coordinate in the taste model.

## 13. Cleaner mathematical replacement

For a validated direction matrix \(D_c\), define a calibrated metric:

\[
M_c\approx
\mathbb E[J_c(a)^TWJ_c(a)]
\]

or a diagonal approximation based on observed effect size. Whiten actions:

\[
\tilde a=L_ca,
\qquad L_c^TL_c=M_c.
\]

Fit ideal points and plan slates in \(\tilde a\)-space, while rendering in original coordinates. This makes temperature, radius, and complexity more interpretable.

## Verdict

**Legacy learner mathematics:** reasonable approximate baseline, not exact replayable Bayes.  
**Numerical issue:** line search can accept a degrading step.  
**Embedding basis:** empirically plausible, mathematically unvalidated and potentially ill-conditioned.  
**Planner:** clean code but acquisition and geometry are heuristic.  
**Promotion gate:** validate and calibrate the representation before interpreting latent centers as tastes.
