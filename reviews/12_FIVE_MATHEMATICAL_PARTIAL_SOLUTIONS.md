# Five Mathematical Partial Solutions for Round 2

**Status:** proposed experiments, not a unified replacement architecture  
**Tracking issue:** [#10](https://github.com/nbardy/art-optimizer/issues/10)

The Round 1 failure is multi-causal. The correct response is not to nominate one fashionable algorithm as the answer. This document proposes five narrow mathematical interventions. Each targets one failure, declares what data it needs, and states what it does **not** solve.

## Summary

| Approach | Specific problem | Primary object |
|---|---|---|
| 1. Perceptual pullback metric + DPP slate | action-diverse but visually duplicate candidates | action-to-image local geometry |
| 2. Seed/control factorial slate | novelty and attribute preference are confounded | stochastic and semantic factors |
| 3. Bayesian directional concept mixture | singleton lanes and concept proliferation | repeated action/visual deltas |
| 4. Typed command-intent likelihood | reroll conflates novelty and rejection | observation semantics |
| 5. Parent-conditioned transport | selection does not create a visual descendant | image/latent inheritance |

## 1. Perceptual pullback metric and output-diverse slate selection

### Target problem

The planner currently measures diversity with Euclidean distance in the eight-dimensional action space. The renderer can map distant actions to nearly identical images.

### Mathematical idea

Let:

\[
I=G_\theta(a,z,c)
\]

be the rendered image and:

\[
\phi(I)\in\mathbb R^m
\]

be a meaningful image representation.

Around anchor action \(a_0\), estimate the local Jacobian:

\[
J(a_0)=\frac{\partial \phi(G_\theta(a,z,c))}{\partial a}\bigg|_{a=a_0}.
\]

The induced local perceptual metric is:

\[
M(a_0)=J(a_0)^\top WJ(a_0)+\epsilon I.
\]

Then distance between nearby actions is measured as:

\[
d_M(a_i,a_j)^2=(a_i-a_j)^\top M(a_0)(a_i-a_j).
\]

This is a pullback of image-space geometry into action space. It answers a concrete question:

> Which numerical action differences are likely to be visibly different here?

### Slate objective

Given hidden candidate pool \(P\), choose slate \(S\) by:

\[
S^*=\arg\max_{|S|=k}
\left[
\sum_{i\in S}\left(\mu_i+\beta\sigma_i\right)
+\lambda\log\det(K_S+\eta I)
\right],
\]

where \(K_S\) is a kernel built from actual or predicted image embeddings.

The log-determinant term is a determinantal point process-style diversity objective. It penalizes redundant candidates even when their action vectors differ.

### Practical versions

**Version A — hidden low-resolution render pool**

1. propose 16–32 actions;
2. render at 256–384 pixels;
3. embed images;
4. select four by utility, uncertainty, and log-det diversity;
5. rerender chosen four at final resolution if needed.

**Version B — learned local surrogate**

Fit:

\[
\Delta\phi\approx \widehat J\Delta a
\]

from recent rendered probes. Use the surrogate to score a large pool cheaply, then render only the selected slate.

### Data-model additions

```text
VisualFeature
    encoder_revision
    vector_digest
    vector/object-store reference

LocalMetricSnapshot
    anchor_design_id
    control_basis_revision
    feature_revision
    estimated_jacobian
    regularization
    validity_radius

SlateSelectionReceipt
    hidden_pool_id
    utility scores
    uncertainty scores
    pairwise perceptual kernel
    selected candidate IDs
```

### Evaluation

- mean and minimum pairwise perceptual distance;
- duplicate rate;
- human “meaningfully different” judgments;
- time-to-first-liked candidate;
- preservation of utility compared with top-four-by-score.

### What it does not solve

It does not make the current image a generative parent. It does not discover semantic concepts. It only fixes the mismatch between action-space and output-space diversity.

## 2. Two-factor seed/control experimental design

### Target problem

The current same-seed slate supports causal attribution but produces low composition diversity. Fresh seeds add novelty but make it unclear whether the user preferred an attribute or a lucky stochastic realization.

### Mathematical idea

Treat semantic control \(a\) and stochastic realization \(z\) as separate factors.

A correlated stochastic root can be generated as:

\[
z(\rho)=\rho z_0+\sqrt{1-\rho^2}\,\epsilon,
\qquad \epsilon\sim\mathcal N(0,I).
\]

The candidate policy declares \(\rho\):

```text
rho = 1.0     exact same root
rho ≈ 0.9     nearby stochastic realization
rho = 0       independent root
```

### Hybrid four-candidate design

A first factorial slate:

| Candidate | Semantic factor | Stochastic factor |
|---|---|---|
| A | small local action change | same root |
| B | large or orthogonal action change | same root |
| C | preferred/local action | fresh or correlated root |
| D | broad/alternate action | fresh root |

A more diagnostic 2×2 slate can hold two actions across two roots:

```text
A1: action A, root 1
A2: action A, root 2
B1: action B, root 1
B2: action B, root 2
```

### Hierarchical preference model

Model candidate utility as:

\[
u_{ij}=f(a_i)+g(z_j)+h(a_i,z_j)+\varepsilon_{ij}.
\]

- \(f(a_i)\): attribute/control preference;
- \(g(z_j)\): stochastic realization effect;
- \(h(a_i,z_j)\): interaction between action and realization.

Repeated crossed observations allow the system to avoid mistaking one lucky seed for a durable concept.

### Data-model additions

```text
NoiseProvenance
    noise_id
    parent_noise_id
    seed
    relation_kind
    rho

CandidateFactorization
    action_id
    noise_id
    semantic_group_id
    stochastic_group_id
```

### Evaluation

- visual diversity versus same-seed baseline;
- ability to predict held-out preference across seeds;
- rate at which concepts survive a new seed;
- user understanding of “refine” versus “another realization.”

### What it does not solve

Fresh roots are still fresh generations. This does not create pixel/latent inheritance from the selected image. It separates stochastic novelty from semantic movement.

## 3. Bayesian directional mixture for provisional concepts

### Target problem

The browser concept library creates active concepts from singleton action deltas and merges only by high cosine similarity in action space.

### Observation model

For a committed comparison, form:

\[
\Delta a_t=a_t^{+}-a_t^{0}
\]

and:

\[
\Delta\phi_t=\phi(I_t^{+})-\phi(I_t^{0}).
\]

Construct a normalized joint directional observation:

\[
x_t=\operatorname{normalize}
\left[
\lambda_a\operatorname{normalize}(\Delta a_t),
\lambda_v\operatorname{normalize}(\Delta\phi_t),
\lambda_m m_t
\right],
\]

where \(m_t\) contains context such as seed relation, prompt/world identity, and outcome type.

### Directional mixture

Use a von Mises–Fisher mixture:

\[
p(x_t\mid k)=C_d(\kappa_k)\exp(\kappa_k\mu_k^\top x_t).
\]

Each component has:

- mean direction \(\mu_k\);
- concentration \(\kappa_k\);
- evidence mass;
- positive and opposition evidence;
- model/control-basis scope;
- exemplar set;
- lifecycle state.

A finite mixture with a birth threshold is enough initially. A Dirichlet-process or Chinese-restaurant-process prior is an optional later experiment, not a requirement.

### Lifecycle

```text
observation
    → unassigned/provisional
    → candidate component
    → active concept after repeated support
    → dormant if not currently relevant
    → split/merge after posterior diagnostics
```

Promotion should require, for example:

- at least 3 independent supporting comparisons;
- posterior assignment confidence above a threshold;
- evidence from at least 2 stochastic roots or contexts;
- visual-delta consistency;
- nonredundancy with existing active components.

### Composition

A concept action should be estimated by regression from concept membership to successful actions, not simply the normalized first delta. The visual concept and the generator action are related but distinct:

```text
ConceptComponent
    visual distribution
    context distribution
    evidence

ConceptActionHead
    control_basis_revision
    predicted action direction
    uncertainty
    validity context
```

### Data-model additions

```text
ConceptObservation
ConceptComponent
ConceptMembership
ConceptLifecycleEvent
ConceptActionHead
ConceptExemplar
```

### Evaluation

- singleton/provisional rate;
- active concept count per 50 interactions;
- held-out assignment likelihood;
- concept stability across seeds;
- human judgments that exemplars share a recognizable property;
- recast preservation.

### What it does not solve

A statistically coherent cluster may still lack a clean natural-language name. It also does not prove the cluster is causally controllable. Naming and generator transport remain separate problems.

## 4. Typed command-intent likelihood

### Target problem

The same visible command currently requests more candidates and provides negative preference evidence.

### Mathematical idea

Do not infer preference where the user has not supplied it. Define typed observations:

```text
Choose(candidate)
NoneOfThese(exposed_set)
ShuffleRequested(policy)
Broken(candidate)
Favorite(design)
Export(design)
```

Only `Choose` and `NoneOfThese` enter the branch-local discrete-choice likelihood by default.

For a choose event:

\[
P(y=j\mid S)=
\frac{\exp(u_j/\tau)}
{\exp(u_0/\tau)+\sum_{i\in S}\exp(u_i/\tau)}.
\]

For none-of-these:

\[
y=0,
\]

where alternative zero is the anchor.

For shuffle:

\[
\mathcal L_{\text{preference}}=0.
\]

The event can still update novelty/fatigue state without changing aesthetic preference.

### Optional latent-intent model

If a deliberately ambiguous low-friction control is later desired, introduce latent intent \(q_t\):

\[
q_t\in\{\text{novelty},\text{rejection},\text{render failure}\}.
\]

But explicit actions should be preferred before fitting a latent model to avoidable ambiguity.

### Data-model additions

```text
CommandFact
    kind
    visible_label
    semantic_contract_version
    preference_effect
    novelty_effect
    qualified alternatives
```

### Evaluation

- comprehension test: what users think each command trains;
- posterior changes after shuffle versus none-of-these;
- rate of accidental negative training;
- novelty satisfaction and reroll frequency.

### What it does not solve

Correct observation semantics will not make four near-duplicate images interesting. It fixes training truthfulness and user trust.

## 5. Parent-conditioned transport with preservation constraints

### Target problem

A selected image is currently a navigation anchor but not a generative parent.

### Treatment separation

Add a renderer mode:

```text
search
    prompt + seed/noise + absolute action

edit
    parent image/latent + requested movement + preservation constraints
```

The experiment must make renderer mode explicit in world/design provenance.

### Constrained objective

Let parent image be \(I_t\) and requested control movement be \(d\). The edit renderer produces:

\[
I_{t+1}=T_\theta(I_t,d,z).
\]

A useful training or search objective is:

\[
\mathcal J=
-u(I_{t+1})
+\lambda_{\text{id}}D_{\text{id}}(I_{t+1},I_t)
+\lambda_{\text{content}}D_{\text{content}}(I_{t+1},I_t)
+\lambda_{\text{off}}D_{\text{off-target}}(I_{t+1},I_t;d).
\]

The preservation terms should be chosen by domain:

- identity/subject embedding;
- structure or segmentation;
- layout/depth;
- color/style locks;
- text/layout preservation;
- region masks.

### Candidate slate

An edit-focused slate could intentionally vary:

```text
edit amount
preservation strength
stochastic detail
one orthogonal alternative
```

This is closer to Shimizu's fine-tuning/Axis spirit because the user can inspect controlled amounts of one learned movement around a real design.

### Data-model additions

```text
ParentConditioning
    parent_design_id
    parent_image_digest
    inversion/latent reference
    edit mask/reference set
    preservation profile

DesignState
    renderer_mode
    generative_parent_id
    navigation_parent_id
```

Navigation ancestry and generative ancestry must be separate fields.

### Evaluation

- human judgment of descendant inheritance;
- preservation of selected subject/layout/details;
- intended edit strength;
- off-target drift;
- preference versus the search baseline;
- branch recoverability and replay.

### What it does not solve

True descendants do not automatically create good concepts or a good exploration policy. This approach only addresses the mismatch between “continue from this image” and fresh text-to-image generation.

## Combined experiment order

These approaches should not all land at once.

1. Typed commands — low implementation risk, fixes semantic harm.
2. Hybrid seed/control slate — immediate visible diversity experiment.
3. Perceptual reranking — closes the planner/output loop.
4. Provisional visual/action concept mixture — requires meaningful embeddings and more data.
5. Parent-conditioned renderer — largest renderer/data-model experiment.

The baseline should remain available throughout. Each intervention should have an ablation and its own promotion criterion.
