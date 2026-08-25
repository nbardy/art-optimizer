# Track MM-1 — Formal Problem Statement and Mathematical Landscape

## Executive finding

The repository contains several equations and competent local algorithms, but it does not yet contain a single mathematical problem statement that cleanly separates:

1. the renderer representation;
2. preference prediction;
3. latent taste discovery;
4. active candidate selection;
5. reusable transformation learning;
6. cross-seed/image validation.

As a result, implementation choices such as Euclidean ideal points, sticky transitions, authored axes, and gallery strength are treated as the problem itself rather than one candidate solution.

This note defines a handoff-ready landscape: a mathematician should be able to replace one object without having to infer product semantics from UI code.

## 1. Primitive spaces and objects

### Generative context

Let

\[
c=(m,r,\kappa,p,s,B,\eta)
\]

be a declared context containing:

- model/checkpoint identity \(m\);
- renderer policy and numerical revision \(r\);
- codec/conditioning policy \(\kappa\);
- prompt or other base condition \(p\);
- stochastic root/seed/noise identity \(s\);
- concrete control basis \(B\);
- remaining generation settings \(\eta\).

Contexts must have a canonical digest. Two observations can share a preference model only under a declared transport relation between their contexts.

### Action space

For context \(c\), let

\[
\mathcal A_c\subseteq\mathbb R^{d_c}
\]

be the valid action domain. The current implementation uses \([-1,1]^8\), but the mathematical object should not assume eight dimensions.

### Renderer

\[
G_c:\mathcal A_c\rightarrow\mathcal I
\]

maps an action to a rendered image or media artifact. For a deterministic fixed-root experiment, \(G_c\) should be deterministic up to the declared replay tolerance. If generation is stochastic beyond \(s\), write a distribution \(P(I\mid a,c)\).

### Observation feature maps

Optional diagnostics:

\[
\phi:\mathcal I\rightarrow\mathbb R^q
\]

for visual features, and

\[
J_c(a)=D(\phi\circ G_c)(a)
\]

for a local action-to-visual Jacobian when estimable.

The preference likelihood need not consume \(\phi\); however, claims of visual coherence or reusable attributes require some observable or human-judgment test beyond action coordinates.

### Choice slate

At interaction \(t\), the system presents:

\[
S_t=(a_{t0},a_{t1},\ldots,a_{tn_t})
\]

where \(a_{t0}\) is the explicit anchor/current image and the remaining actions are qualified exposed alternatives. Record display positions separately from mathematical alternative identity.

### Outcome

\[
y_t\in\{0,1,\ldots,n_t\}
\]

selects the anchor or one candidate. Other commands such as exploration, broken render, preview, and gallery browsing are separate event types and do not enter this likelihood.

## 2. Separate mathematical goals

### Goal A — predict preferences

Given past evidence \(E_{<t}\), predict the full categorical distribution:

\[
P(y_t=j\mid S_t,c_t,E_{<t}).
\]

Evaluation:

- prequential log loss;
- calibration;
- Brier score;
- residuals by position, role, radius, and context;
- decision usefulness at matched generation budget.

### Goal B — discover multiple preference modes

Introduce latent state \(z_t\) representing a mode/taste:

\[
z_t\in\{1,\ldots,K\}.
\]

Infer:

- number or effective number of modes;
- state responsibilities \(P(z_t=k\mid E)\);
- each mode's preference function;
- temporal/branch transition structure;
- stable component identity and uncertainty.

A taste is not automatically a visual attribute. It is initially a component of the preference model.

### Goal C — choose informative/useful candidate slates

Given current posterior \(\Pi_t\), choose:

\[
S_{t+1}=\arg\max_{S\in\mathcal S(c_t)}
\mathcal U(S;\Pi_t,\text{product objective})
\]

where \(\mathcal U\) may combine:

- expected user utility;
- information gain;
- exploration coverage;
- trust-region constraints;
- render cost;
- explicit product roles.

This is distinct from fitting preferences.

### Goal D — learn reusable generative directions

Given intervention deltas \(\delta_t=a_{ty}-a_{t0}\), infer directions or a low-rank basis \(D\) that produces repeatable effects across held-out contexts.

A proposed direction \(d\) should pass a transfer test such as:

\[
T(d)=\mathbb E_{c,a}
[\operatorname{consistency}(G_c(a+\lambda d),G_c(a),\lambda)]
\]

under declared contexts and strengths. Selection frequency alone is insufficient.

### Goal E — validate a taste as a generative image family

For taste component \(k\), define a generator/probe distribution over actions and seeds, then test whether outputs share a human-recognizable or feature-consistent family while remaining diverse.

This is what the seed-by-strength gallery begins to visualize. It is a separate validation problem from latent choice-mode discovery.

## 3. Candidate preference-function families

### Ideal point

Current model:

\[
u_k(a)=-\frac12(a-\theta_k)^TQ_k(a-\theta_k).
\]

Advantages:

- compact;
- interpretable center;
- convex MAP fitting for fixed positive-definite \(Q_k\);
- easy gallery probing.

Limitations:

- unimodal convex preference region;
- depends strongly on coordinate geometry;
- cannot express ridges, rings, disjoint regions, or directional monotonic preference;
- \(Q=I\) assumes calibrated independent axes.

### Linear or quadratic utility

\[
u_k(a)=w_k^T\psi(a)
\]

with a declared feature map. Flexible but feature geometry and regularization matter.

### Gaussian process / kernel utility

\[
u_k\sim\mathcal{GP}(0,K_c).
\]

Useful for nonlinear local preference, but active learning and multi-mode identity become more expensive. Kernel choice must follow validated representation geometry.

### Neural or representation-conditioned utility

Possible later, but inappropriate before enough evidence and strong replay/provenance exist.

## 4. Candidate latent-mode structures

### Finite mixture, exchangeable

\[
P(y_t\mid S_t)=\sum_k\pi_k P(y_t\mid S_t,k).
\]

No temporal continuity. Simple baseline.

### Sticky hidden Markov model

\[
P(z_t=j\mid z_{t-1}=i)=\rho\mathbf1[i=j]+(1-\rho)\pi_j.
\]

Matches the current intuition that nearby interactions often remain in one creative mode. Requires careful definition of sequence adjacency under branch restores and task changes.

### Semi-Markov model

Models explicit duration in a taste. Potentially more natural if sessions contain long mode runs.

### Nonparametric mixture / HDP-HMM

Allows unbounded components but brings substantial inference and hyperparameter complexity. It should be a comparison model, not the first implementation.

### Explicit user-controlled modes

Manual spawn/switch is not incompatible with emergence. It supplies high-value structural labels and can coexist with automatic suggestions.

## 5. Choice likelihood

For utility \(u_k\) and temperature \(\tau\):

\[
P(y_t=j\mid S_t,z_t=k)
=
\frac{\exp(u_k(a_{tj})/\tau)}
{\sum_{\ell=0}^{n_t}\exp(u_k(a_{t\ell})/\tau)}.
\]

If exposure or judgment quality yields an observation weight \(\omega_t\), state explicitly whether this is:

- a powered likelihood \(P(y_t\mid\cdot)^{\omega_t}\) (generalized Bayes);
- a replicated/fractional count approximation;
- a separate noise model.

Do not silently mix these interpretations.

Position bias, role labels, and reveal order should be randomized/counterbalanced or explicitly modeled:

\[
u_{tk}(a,j)=u_k(a)+b_{\text{position}(j)}+r_{\text{role}(j)}.
\]

## 6. Priors and identifiability

A complete specification must state:

- prior on \(K\) or model-selection policy;
- prior on \(\theta_k\);
- whether \(Q_k\) is fixed, learned, or calibrated from renderer geometry;
- prior on prevalence \(\pi\);
- prior/fixed value for stickiness \(\rho\);
- temperature \(\tau\);
- label/lineage convention;
- constraints preventing equivalent rescalings.

Coordinate scale and temperature are confounded. If action axes are rescaled, \(Q\) or \(\tau\) must change accordingly.

## 7. Required mathematical outputs

A mathematician should be asked to return these objects, not “a better optimizer”:

```text
RepresentationScope
ChoiceObservation
TastePosterior
PredictiveDistribution
ComponentAssignmentPosterior
ModelComparisonReceipt
SlateAcquisitionFunction
DirectionTransferTest
GenerativeFamilyValidationReceipt
```

Suggested functional API:

```python
fit(observations, policy) -> TastePosterior
predict(posterior, slate) -> CategoricalDistribution
assign(posterior, observations) -> ResponsibilityMatrix
compare(model_posteriors, prequential_receipts) -> ModelComparisonReceipt
propose(posterior, context, budget) -> SlateWithAcquisitionReceipt
validate_direction(direction, heldout_contexts) -> DirectionTransferReceipt
validate_taste_family(component, seed_strength_probes) -> FamilyValidationReceipt
```

Every output should include numerical diagnostics and a revision/digest.

## 8. Falsification landscape

The model should be rejected or narrowed when:

- one taste repeatedly predicts as well as multiple tastes;
- components are not stable under modest data perturbation;
- mode assignments are explained by screen position or planner role;
- a taste center produces no coherent gallery across seeds;
- action-space distance has little visual effect;
- a learned direction fails on held-out anchors;
- posterior uncertainty stays broad despite confident UI labels;
- inference depends materially on arbitrary initialization;
- replay under the same facts changes beyond tolerance.

## 9. What the current implementation chooses

The current code instantiates one point in this landscape:

```text
A_c = [-1,1]^8
Q_k = beta * I
K in {1,2,3}
sticky HMM
Gaussian center prior
powered multinomial-logit observations
MAP/EM fit
prequential observed-winner log score
ad hoc complexity and evidence gates
legacy planner remains authoritative
```

That is a reasonable prototype baseline. It should be represented as one model policy, not the mathematical definition of taste.

## Verdict

The problem is mathematically tractable and has a clean decomposition, but the repository needs a normative document at this level. Once written, a mathematician can independently improve the preference family, latent process, inference, model comparison, or acquisition function without changing command semantics or renderer provenance.
