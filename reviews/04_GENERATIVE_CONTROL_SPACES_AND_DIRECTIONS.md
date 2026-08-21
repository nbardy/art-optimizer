# Research Review 4/5: Generative Control Spaces and Learned Directions

## 1. Review question

What does it mean to apply a learned visual “direction” in different quantities, and which generator representation should Art Optimizer search?

The word *latent* is too vague to answer this. Modern generators expose several mathematically different spaces:

- integer seeds;
- materialized initial noise;
- prompt and text-embedding conditions;
- reference-image conditions;
- generator latent variables;
- layer activations and attention states;
- adapter or LoRA weights;
- scheduler and guidance parameters;
- image-editing/inversion states.

A direction is only meaningful with respect to a named space, model revision, context, and validity region.

## 2. A control-space formalism

Write a generator as:

\[
I=G_\theta(s,c,a),
\]

where:

- \(s\) is a stochastic root, usually a materialized noise state;
- \(c\) contains fixed world conditions such as prompt, references, aspect ratio, and model profile;
- \(a\in\mathcal A\) is a compact control action;
- \(I\) is the rendered image.

A direction \(d\) in action space produces:

\[
a(\alpha)=a_0+\alpha d.
\]

The UI's “amount” is the scalar \(\alpha\). This expression is useful only if:

1. nearby \(\alpha\) values produce reasonably continuous images;
2. the perceptual effect is consistent enough to compare;
3. unrelated attributes do not change catastrophically;
4. the direction's scope is recorded;
5. the generator can replay the same state.

A vector without those properties is still a perturbation, but it is not yet a usable design direction.

## 3. Integer seeds are not a metric space

An integer seed is a key for a pseudorandom-number generator. In general:

```text
seed 1000
seed 1001
```

produce unrelated tensors. There is no reason for numerical adjacency in seed integers to imply perceptual adjacency.

Therefore this is not meaningful:

\[
s'=s+\alpha d_s
\]

when \(s\) denotes the integer seed.

The materialized initial noise tensor is different:

\[
z_0\in\mathbb R^N,
\qquad z_0\sim\mathcal N(0,I).
\]

It supports interpolation and local directions. One useful correlated resampling is:

\[
z'
=\rho z_0+\sqrt{1-\rho^2}\,\epsilon,
\qquad \epsilon\sim\mathcal N(0,I).
\]

Interpretation:

- \(\rho\approx1\): small stochastic variation;
- intermediate \(\rho\): broader structural change;
- \(\rho=0\): independent new root.

For Art Optimizer, this motivates a simple initial rule:

> Hold materialized noise fixed while learning semantic/control preferences inside a world; draw a new stochastic root only for New world.

This improves attribution. When all four candidates share the same root and world conditions, their differences are more plausibly caused by their control actions.

## 4. Noise directions: useful but local

One may define:

\[
z(\alpha)=z_0+\alpha d_z.
\]

However, unrestricted Euclidean movement can change the norm and move away from the Gaussian typical shell. A norm-preserving local tangent construction is safer. Let:

\[
\hat z_0=\frac{z_0}{\lVert z_0\rVert},
\]

and let \(B_z\) span tangent directions orthogonal to \(\hat z_0\). For a low-dimensional coefficient \(v\):

\[
z(v)
=r\left[
\cos(\lVert v\rVert)\hat z_0
+
\sin(\lVert v\rVert)
B_z\frac{v}{\lVert v\rVert}
\right].
\]

Noise controls can produce valuable changes in pose, composition, texture realization, and geometry. They are usually:

- highly local to one root;
- weakly semantic;
- difficult to transfer across parent images;
- easily confounded with lucky composition.

Art Optimizer should label them as **world-local structural variation controls**, not universal user-taste directions.

A useful diagnostic slate occasionally repeats semantic controls across noise variants:

```text
A1 = direction A, noise variant 1
A2 = direction A, noise variant 2
B1 = direction B, noise variant 1
B2 = direction B, noise variant 2
```

This factorial structure helps estimate whether the user preferred a control direction or one fortunate stochastic realization.

## 5. GAN latent and activation directions

Early work on GAN control provides the clearest examples of “direction × amount.”

### 5.1 GANSpace

[GANSpace](https://neurips.cc/virtual/2020/public/poster_6fe43269967adbb64ec6149852b5cc3e.html) applies principal component analysis to latent or activation spaces of pretrained GANs and demonstrates controls associated with viewpoint, aging, lighting, time of day, and other transformations. Layer-wise application helps localize an edit to particular generator stages.

The key contribution is simple and durable:

> high-variance directions in a generator's internal representation can sometimes correspond to coherent, reusable visual controls.

But PCA optimizes variance, not user relevance, disentanglement, or causal semantics. A principal component can combine several perceptual factors.

### 5.2 Unsupervised direction discovery

[Voynov and Babenko (2020)](https://proceedings.mlr.press/v119/voynov20a.html) learn latent directions in a pretrained GAN without external labels by training a reconstructor to identify which direction and magnitude produced a generated transformation. Their method reveals interpretable transformations such as zoom, recoloring, and background changes.

This establishes that useful directions need not be predefined by text or attributes. It also suggests a future Art Optimizer path:

1. discover a bank of model-native transformation directions;
2. let preference learning infer which combinations matter to a user;
3. retain direction semantics only when empirically validated.

### 5.3 Limits of GAN precedents

GAN direction methods often assume:

- one model trained for one image domain;
- a relatively compact latent or style space;
- no long text prompt;
- one-shot generation rather than iterative denoising;
- stable global semantics within the training distribution.

Modern text-to-image flow/diffusion transformers have richer conditioning and intervention surfaces. GAN results establish possibility, not direct transfer.

## 6. Text and CLIP-guided directions

[StyleCLIP](https://doi.org/10.1109/ICCV48922.2021.00209) uses CLIP to connect text descriptions with StyleGAN manipulation. The paper presents:

- per-image latent optimization under a CLIP objective;
- learned latent mappers for a target text description;
- input-agnostic global directions in StyleGAN style space.

This work is especially relevant to Art Optimizer's model codec because it separates:

```text
semantic instruction
    neutral text -> target text

control representation
    a direction in the generator's internal style space

amount
    manipulation strength
```

Art Optimizer's current prompt-embedding codec follows a related high-level pattern. For each semantic axis, it encodes negative and positive endpoint prompts and constructs:

\[
d_i
=\frac{E(p_i^+)-E(p_i^-)}{2}.
\]

The world action produces:

\[
E(a)
=E(p_0)
+
\frac{\eta}{\sqrt d}
\sum_i a_i d_i.
\]

This creates a compact and inspectable control basis without training an adapter. It is an experimental basis, not proof that text-embedding differences are linear semantic controls in every model.

### 6.1 Strengths of embedding controls

- simple to construct for a new prompt;
- direct embedding-level access;
- differentiable;
- compatible with fixed seed and world conditions;
- easy to version and replay;
- semantic endpoints are human-readable;
- model-specific adapters can preserve one canonical action type.

### 6.2 Failure modes

- token alignment and masks can differ across endpoint prompts;
- large embedding arithmetic may leave the model's familiar conditioning manifold;
- axes can interact nonlinearly;
- text encoders can entangle content, style, and composition;
- equal coefficient changes need not produce equal perceptual changes;
- the same axis can behave differently across prompts, seeds, and models;
- semantic endpoint phrases can dominate or erase the base prompt.

These are reasons for a control-basis benchmark, not reasons to avoid embedding experiments.

## 7. Feedback-image and attention controls

### 7.1 FABRIC

[FABRIC](https://doi.org/10.1007/978-3-031-91907-7_23) introduces a training-free method that conditions diffusion generation on sets of positive and negative feedback images by injecting reference information through self-attention. It demonstrates an iterative loop in which feedback examples steer later generations without fine-tuning the base model.

FABRIC supplies a concrete generative mechanism for Art Optimizer's persistent exemplars:

```text
preference learner
    decides which historical images are positive/negative/relevant

generative mechanism
    injects selected examples into attention/reference conditioning
```

The preference model and conditioning mechanism should remain separate. A favorite is evidence; it does not automatically specify which layer or attention weight should be changed.

### 7.2 MultiBO

[MultiBO](https://arxiv.org/abs/2602.02388) optimizes a constrained low-dimensional family of self-attention transformations through multi-choice preferential Bayesian optimization. Its reported results support searching a compact attention-intervention space rather than raw initial noise under a limited human query budget.

For Art Optimizer, attention controls are attractive because they may alter structure and semantics while retaining one fixed model. Their risks include:

- architecture-specific implementation;
- weak transfer across checkpoints;
- difficult interpretability;
- layer and timestep sensitivity;
- a limited reachable image set when the intervention family is too narrow.

## 8. Adapter and model-merging controls

LoRA and other lightweight adapters define a natural continuous action space:

\[
\theta(a)
=\theta_0+\sum_{k=1}^{K}a_k\Delta\theta_k.
\]

[GimmBO](https://arxiv.org/abs/2601.18585) treats weights over a library of diffusion adapters as a design space and uses preferential Bayesian optimization to help users search mixtures that would be difficult to tune manually. Its two-stage optimizer exploits the sparsity and constrained ranges common in real adapter mixtures.

This is nearly the literal “different directions in different quantities” interaction:

```text
adapter A  0.30
adapter B -0.10
adapter C  0.75
```

The strengths are:

- controls are persistent and replayable;
- a coefficient has clear parameter-space meaning;
- style/subject modules can be reused;
- sparse combinations are possible;
- offline learned user adapters can enter the same representation.

The limitations are:

- the initial direction bank is supplied rather than discovered online;
- adapters can interfere nonlinearly;
- compatibility depends on base model and training method;
- a library can impose its own aesthetic monoculture;
- merging weights do not guarantee perceptual linearity.

A future Art Optimizer codec can expose adapter coordinates beside embedding, reference, or attention coordinates, but each block must be named and versioned.

## 9. A hybrid action manifold

The most capable future representation is not one undifferentiated latent vector. It is a structured action:

\[
a=
\begin{bmatrix}
a_{\text{text}}\\
a_{\text{reference}}\\
a_{\text{attention}}\\
a_{\text{adapter}}\\
a_{\text{noise}}
\end{bmatrix}.
\]

Each block has different semantics and scope.

| Block | Likely effect | Scope | Transfer expectation |
|---|---|---|---|
| Text/conditioning | semantic/style/composition instruction | prompt + model | moderate, model-specific |
| Reference weights | selected exemplar influence | fixed reference set | world/model-specific |
| Attention | structure/feature routing | layers/timesteps/model | strongly model-specific |
| Adapter weights | learned subject/style modules | base checkpoint | checkpoint family |
| Noise tangent | pose/layout/realization | one stochastic root | highly local |

The service should expose one unified typed action object, but should not pretend all blocks share the same geometry.

## 10. Learning directions from preference data

Suppose an image feature map is:

\[
\Phi(a)=\phi(G_\theta(s,c,a)).
\]

From preferred and rejected examples, a regularized feature-space preference direction can be estimated as:

\[
d_\phi
=(\Sigma_\phi+\lambda I)^{-1}
(\bar\phi_+-\bar\phi_-).
\]

To obtain a generator-control direction, use the local Jacobian:

\[
J(a)=\frac{\partial\Phi(a)}{\partial a}.
\]

Solve:

\[
d_a
=\arg\min_d
\lVert Jd-d_\phi\rVert_W^2
+\lambda\lVert d\rVert_2^2,
\]

with solution:

\[
d_a
=(J^\top WJ+\lambda I)^{-1}J^\top Wd_\phi.
\]

This is a local pullback: it finds the control-space movement most likely to realize the preferred visual movement.

When full differentiation is unavailable, estimate:

\[
\Delta\phi_i\approx \hat J\,\Delta a_i
\]

from the perturbations the system already renders.

## 11. Multiple user-relevant directions

A single utility gradient only gives the steepest local improvement. To identify several useful control combinations, define an active-subspace matrix:

\[
C=\mathbb E\left[\nabla_a f(a)\nabla_a f(a)^\top\right].
\]

Its leading eigenvectors identify action combinations along which predicted preference changes most.

Ordinary Euclidean orthogonality is insufficient because two parameter vectors may look perceptually identical. Define a local perceptual metric:

\[
M(a)=J(a)^\top WJ(a)+\epsilon I.
\]

Then seek:

\[
d_i^\top M(a)d_j=\delta_{ij}.
\]

This makes directions locally distinct in image space rather than merely perpendicular in coefficient space.

## 12. Perceptual amount calibration

Equal coefficient increments are rarely equal visual increments. For direction \(d\), define perceptual arclength:

\[
s(\alpha)
=\int_0^\alpha
\sqrt{d^\top M(a_0+td)d}\,dt.
\]

Render several samples, estimate \(s(\alpha)\), fit a monotone map, and expose approximately uniform perceptual steps.

This is important for UI sliders and axis sweeps. Otherwise the first eighty percent of a slider can appear inert and the last twenty percent can destroy the image.

## 13. Direction identity and scope

Every learned direction should be stored with:

```text
direction ID
space/block type
model and checkpoint revision
codec/control-basis revision
anchor world/design, if local
prompt and reference context
normalization and amount calibration
validity radius
source evidence
feature encoder revision
creation algorithm and version
```

A direction can have one of several scopes:

- **global:** transfers across many prompts and roots under one model;
- **contextual:** valid for one prompt/reference family;
- **world-local:** valid for one root and world;
- **anchor-local:** valid only near one design state.

Scope should be demonstrated, not guessed from how interpretable a five-image sweep looks.

## 14. Cross-model codecs

FLUX and Krea can share semantic axis names while maintaining distinct numerical bases:

```text
composition
form
palette
lighting
...
```

But the coefficient \(a_3=0.7\) does not automatically have the same effect in both models.

Therefore:

- control-basis revisions remain model-specific;
- action centroids in the persistent atlas are filtered by compatible basis;
- model-neutral preference features may transfer;
- model-specific control heads must be learned or validated separately;
- cross-model direction transport is an experiment, not a default.

## 15. Validation protocol

A candidate basis should be tested with one-dimensional sweeps:

\[
a(\alpha)=a_0+\alpha e_i,
\qquad
\alpha\in\{-1,-0.5,0,0.5,1\}.
\]

Across prompts and roots, measure:

### Responsiveness

Does the image change enough for a human to judge?

### Smoothness

Are adjacent steps more similar than distant steps?

### Monotonicity

Does the intended property change consistently with \(\alpha\)?

### Preservation

Do unrelated subject, identity, layout, or text attributes remain stable when they should?

### Independence

Are coordinate effects distinguishable, or is the basis redundant?

### Transfer

Does the direction behave similarly across roots, prompts, and worlds within its claimed scope?

### Utility

Can a preference optimizer make faster progress than seed-only, prompt-only, or random-walk baselines?

### Replay

Do the same recorded inputs reproduce the declared artifact or at least the declared best-effort distribution?

## 16. Art Optimizer decisions

### V0

- fix one materialized noise root per world;
- use an eight-dimensional model-specific conditioning codec;
- keep integer seed out of the action vector;
- preserve exact model/codec/control provenance;
- treat the control basis as experimental;
- keep FLUX and Krea action coordinates separate;
- use New world for independent stochastic roots.

### Next experiments

1. prompt embedding directions versus prompt-string compilation;
2. fixed reference-image weights from persistent exemplars;
3. local attention interventions;
4. sparse adapter mixtures;
5. correlated/tangent noise dimensions;
6. hybrid action blocks with explicit ablations;
7. learned pullback directions from accumulated preference data.

### Non-claims

Art Optimizer should not claim that:

- integer seeds form a smooth semantic space;
- all prompt-embedding arithmetic produces meaningful directions;
- a named axis is disentangled because its endpoint phrases are readable;
- one basis transfers unchanged between FLUX and Krea;
- noise directions encode persistent taste;
- latent interpolation is perceptually linear;
- the current eight axes are optimal;
- model internals have been validated without the sweep and user-study evidence.

## 17. Citation-safe conclusion

Prior work establishes multiple viable sources of generator control: principal and learned GAN directions, CLIP-guided style directions, feedback-image attention conditioning, attention-warp spaces, and weighted adapter mixtures. Art Optimizer's contribution is to place these behind one versioned codec/action contract and make them searchable through preference feedback. A direction is considered usable only after its local geometry, scope, replay, and perceptual behavior are measured.

## References

- Erik Härkönen, Aaron Hertzmann, Jaakko Lehtinen, and Sylvain Paris. [“GANSpace: Discovering Interpretable GAN Controls.”](https://neurips.cc/virtual/2020/public/poster_6fe43269967adbb64ec6149852b5cc3e.html) NeurIPS, 2020.
- Andrey Voynov and Artem Babenko. [“Unsupervised Discovery of Interpretable Directions in the GAN Latent Space.”](https://proceedings.mlr.press/v119/voynov20a.html) ICML, 2020.
- Or Patashnik, Zongze Wu, Eli Shechtman, Daniel Cohen-Or, and Dani Lischinski. [“StyleCLIP: Text-Driven Manipulation of StyleGAN Imagery.”](https://doi.org/10.1109/ICCV48922.2021.00209) ICCV, 2021.
- Dimitri von Rütte, Elisabetta Fedele, Jonathan Thomm, and Lukas Wolf. [“FABRIC: Personalizing Diffusion Models with Iterative Feedback.”](https://doi.org/10.1007/978-3-031-91907-7_23) ECCV 2024 Workshops, 2024.
- Yuto Nakashima, Mingzhe Yang, and Yukino Baba. [“SwipeGANSpace: Swipe-to-Compare Image Generation via Efficient Latent Space Exploration.”](https://arxiv.org/abs/2404.19693) 2024.
- Chenxi Liu, Selena Ling, and Alec Jacobson. [“GimmBO: Interactive Generative Image Model Merging via Bayesian Optimization.”](https://arxiv.org/abs/2601.18585) 2026.
- Rajalaxmi Rajagopalan, Debottam Dutta, Yu-Lin Wei, and Romit Roy Choudhury. [“Personalized Image Generation via Human-in-the-loop Bayesian Optimization.”](https://arxiv.org/abs/2602.02388) 2026.
