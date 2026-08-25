# Track MC-1 — Ideal-Point, Sticky-HMM, and Model-Selection Correctness

## Executive finding

The per-component ideal-point likelihood and center gradient are mathematically sound. The surrounding sticky-HMM fitting and model-selection machinery has several material problems:

1. the prevalence update is not the M-step for the declared transition model;
2. the convergence objective mixes old likelihood with new parameters;
3. weak observation weights are applied differently in fitting and prequential scoring;
4. predictive probabilities are plug-in MAP values despite posterior language;
5. the complexity penalty ignores most added parameters and is ad hoc;
6. component identity is not stable.

The implementation is a useful prototype, but it should not control candidate generation or support strong taste-discovery claims in its current form.

## 1. Ideal-point likelihood

The code uses, for taste component \(k\):

\[
\ell_{kj}
=-\frac{\beta}{2}\lVert a_j-\theta_k\rVert^2,
\qquad
p_{kj}=\frac{e^{\ell_{kj}}}{\sum_m e^{\ell_{km}}}.
\]

This is implemented in [`_choice_probability`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py).

Expanding the logit:

\[
-\frac\beta2\lVert a_j-\theta\rVert^2
=-\frac\beta2\lVert a_j\rVert^2
+\beta a_j^T\theta
-\frac\beta2\lVert\theta\rVert^2.
\]

The final term is common to every alternative and cancels in the softmax. Therefore the conditional log likelihood is concave in \(\theta\); with a Gaussian prior the MAP objective is strictly concave.

## 2. Center gradient audit — correct

For one observation with winner \(y\), the negative log-likelihood gradient is:

\[
\nabla_\theta[-\log p_y]
=
\beta\left(\mathbb E_p[a]-a_y\right).
\]

With prior \(\theta\sim\mathcal N(0,\sigma_0^2I)\):

\[
\nabla L(\theta)
=
\sigma_0^{-2}\theta
+
\sum_t w_t\beta(\mathbb E_{p_t}[a]-a_{t,y_t}).
\]

[`_optimize_center`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py) implements exactly this sign and scaling.

The Hessian is:

\[
H
=
\sigma_0^{-2}I
+
\sum_t w_t\beta^2\operatorname{Cov}_{p_t}(a),
\]

which is positive definite under the prior. This also provides a straightforward Laplace covariance \(H^{-1}\), but the current code does not calculate or retain it.

## 3. Critical mathematical error — prevalence update is not an HMM M-step

The transition matrix is:

\[
T_{ij}=\rho\mathbf1[i=j]+(1-\rho)\pi_j,
\]

where the code calls \(\pi\) `weights`.

The expected complete-data objective for \(\pi\) includes:

\[
Q(\pi)
=
\sum_j\gamma_{0j}\log\pi_j
+
\sum_{t=1}^{T-1}\sum_{i,j}
\xi_{tij}\log\left[
\rho\mathbf1[i=j]+(1-\rho)\pi_j
\right]
+
\log p(\pi).
\]

The code instead sets:

```python
counts = (responsibilities * observation_weights[:, None]).sum(axis=0)
weights = (counts + 0.6) / (sum_weights + 0.6 * K)
```

This is an occupancy update suitable for an exchangeable mixture, not the M-step for the sticky transition above. The diagonal transition term depends nonlinearly on \(\pi_j\), and expected transition counts \(\xi_{tij}\) are not even computed.

### Clean v1 choices

Either:

1. **fix \(\pi\) to uniform**, estimating only centers; or
2. compute \(\xi\) and numerically maximize the constrained objective; or
3. use a conventional transition matrix with independent Dirichlet rows and a sticky diagonal prior.

Uniform prevalence is the cleanest initial ablation.

## 4. EM convergence objective is invalid

Inside `_run_em`:

1. emissions and `log_likelihood` are computed using old centers and old weights;
2. responsibilities are computed;
3. weights are changed;
4. centers are changed;
5. `objective` is set to old `log_likelihood` minus the prior penalty of new centers.

Thus the value compared across iterations is not the observed-data objective at either the old or new parameter set.

```python
objective = log_likelihood - 0.5 * ||next_centers||² / prior_variance
```

The convergence check can stop early or oscillate without detecting it. It also cannot verify EM monotonicity.

### Fix

After the M-step, recompute emissions and observed-data log likelihood under the new parameters, then add the prior terms. Record the full objective history and convergence reason.

## 5. Weak observation weights are inconsistent across fitting and scoring

For observation weight \(\omega_t\), fitting uses component emissions:

\[
e_{tk}=p(y_t\mid z_t=k)^{\omega_t}
\]

and then marginalizes hidden state:

\[
P_{\text{fit}}(y_t)=\sum_k q_{tk}p_{tk}^{\omega_t}.
\]

Prequential scoring instead computes the ordinary mixture probability and multiplies its log by \(\omega_t\):

\[
\omega_t\log\left(\sum_k q_{tk}p_{tk}\right)
=
\log\left(\sum_kq_{tk}p_{tk}\right)^{\omega_t}.
\]

In general:

\[
\sum_kq_kp_k^\omega
\ne
\left(\sum_kq_kp_k\right)^\omega.
\]

For one component or \(\omega=1\), they coincide. For multi-taste weak `None fit` observations they do not.

The project must choose and document one interpretation:

- tempered conditional emissions inside the latent model; or
- generalized Bayes power on the marginal choice likelihood; or
- an explicit noisy/weak-label observation model.

Training and evaluation should use the same object.

## 6. Predictive probability is MAP plug-in, not posterior predictive

`TasteFit` contains centers but no covariance. `_predictive_probability` evaluates the softmax at fitted centers.

A true posterior predictive is:

\[
P(y\mid S,E)
=
\int P(y\mid S,\Theta)\,p(\Theta,z\mid E)\,d\Theta\,dz.
\]

At minimum, calculate per-center Laplace covariance from the Hessian above and integrate with deterministic QMC or a declared approximation. Otherwise call the result `plug_in_predictive_probability`.

## 7. Model-selection penalty is not tied to parameter count

The code subtracts:

\[
\lambda(K-1)\log(T+1),
\]

with default \(\lambda=0.55\).

An ideal-point HMM with dimension \(d\) adds approximately:

```text
K*d center parameters
K-1 prevalence parameters (if learned)
possibly transition/hyperparameters
```

The current penalty counts only additional component number, not dimensions. Because scores are genuinely prequential, an extra BIC penalty is not automatically required; but the chosen penalty should be derived or treated as a tuned decision threshold, not described as a general complexity cost.

Recommended comparison:

- pure prequential score with proper prior predictive;
- optional decision margin chosen by simulation for false-split control;
- report both, rather than merging them into one opaque penalized score.

## 8. Eligibility gates are heuristics

A multi-component model is eligible when:

```text
T >= 3K
minimum effective mass >= 1.75
```

These values have no calibration study. They may be useful product safeguards, but should be versioned as a promotion policy and tested for false-positive/false-negative taste discovery under simulation.

## 9. Component identity is unstable

`_align_to_warm_start` exists but `fit_state` always calls `_fit(..., warm_start=None)`. Every update refits from scratch.

Display identity is then assigned by first hard appearance. Small data changes can:

- swap Taste A and Taste B;
- move historical exemplars between tastes;
- make a taste disappear and later reappear with a different ID.

For a user-visible taste object, introduce immutable component revisions and match new components to prior components using posterior overlap plus evidence lineage. Label switching should be handled deliberately, not by current display order.

## 10. Missing full predictions and corrupt-event fallback

Each event stores only one probability per model: the probability of the outcome eventually observed. This is enough for log score but not calibration or detailed audit.

Worse, a missing receipt silently becomes uniform probability. Missing or incompatible receipts should:

- fail replay under the declared schema; or
- pass through an explicit migration that records the fallback.

Silent uniform replacement makes a corrupt event look like weak model performance.

## 11. Required correctness tests

1. finite-difference gradient and Hessian for center objective;
2. brute-force hidden-path comparison for small HMMs;
3. exact expected-transition-count tests;
4. M-step objective improvement tests;
5. simulation with unequal prevalence and known persistence;
6. false-split rate under a noisy one-taste generator;
7. calibration of plug-in versus Laplace predictive probabilities;
8. weight-semantics tests for \(\omega<1\);
9. component-label continuity across incremental updates;
10. corruption test: missing prediction receipt must fail.

## Verdict

**Ideal-point component likelihood:** correct.  
**Center gradient:** correct.  
**Sticky prevalence inference:** incorrect for the declared transition model.  
**EM convergence:** mathematically invalid as implemented.  
**Weak-weight semantics:** inconsistent between fit and score.  
**Posterior prediction:** not implemented.  
**Model selection:** useful heuristic, not a clean statistical criterion.
