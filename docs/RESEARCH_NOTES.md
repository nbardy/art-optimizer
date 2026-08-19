# Research Notes

**Status:** Working research synthesis, not a completed literature review  
**Model recommendation cutoff:** 2026-08-19

## 1. Research question

Can a generative image tool infer useful visual directions from lightweight interaction—primarily selecting one of four images, rerolling, starring, restoring history, or starting a new stochastic world—and apply those directions in controllable quantities while preserving fast, high-quality generation?

Art Optimizer joins four ideas:

$$
\text{persistent taste prior}
+
\text{branch-local preference learning}
+
\text{generative control-space optimization}
+
\text{comparison-first interaction}.
$$

It is not only a latent-space browser and not only a recommender. The user explores one evolving design while the system learns both a temporary local goal and, over time, durable preference modes.

## 2. How much of Murdock and Shimizu do we use?

Two projects are load-bearing intellectual precedents:

- Ryan Murdock’s [Generative Recommenders](https://rynmurdock.github.io/writing/generative_recommenders.html), which asks how generation can be conditioned by users’ and peers’ interactions instead of requiring explicit prompts.
- Evan Shimizu’s [Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools](https://www.evanshimizu.com/port/CMU-CS-20-104.pdf), especially Design Adjectives and its gallery/hover interaction model.

For the first single-user implementation:

- **Shimizu is load-bearing for the local design loop.** We use the idea of fitting a subjective function from a small number of judgments and using it to propose the next alternatives. The one-current-design plus previewable suggestions interface is directly aligned with this work.
- **Murdock is initially a lightweight persistent prior.** Favorites, exports, revisits, and selected designs form a durable representation used to initialize new worlds and construct one of the four candidates.
- **Preferential Bayesian optimization and bandit work supply the actual online choice model.** We replace scalar ratings with a four-way choice plus an outside option.
- **Diffusion-specific direction discovery is the largest new integration layer.** Neither precedent solves how to preserve and optimize model, conditioning, initial noise, adapters, attention interventions, and branch provenance together.

A rough conceptual split for the MVP is therefore:

```text
local optimizer and interaction     mostly Shimizu-inspired
persistent taste and unprompted drift partly Murdock-inspired
four-way acquisition policy         preference-BO / bandit literature
control manifold and replay         Art Optimizer integration work
```

These are attribution heuristics, not measurable percentages.

## 3. Ryan Murdock: Generative Recommenders

### 3.1 What it does

Murdock’s Zahir experiment constructs a user–item interaction matrix and fits weighted alternating least squares while constraining learned item representations to remain aligned with corresponding CLIP image embeddings. The resulting user representation can be consumed by a visual generator, either alone or as a direction combined with another condition.

The experiment uses [FLICKR-AES](https://openaccess.thecvf.com/content_ICCV_2017/papers/Ren_Personalized_Image_Aesthetics_ICCV_2017_paper.pdf), which is unusually useful because it contains user identities and overlap among rated images. Murdock reports iterative qualitative experiments in which generated images are rated and added back into the interaction data, causing later generations to move toward regions he finds compelling.

The later [Preference Prior](https://github.com/rynmurdock/preference-prior) project conditions on a sequence of preferred-media embeddings and predicts a held-out preferred-media embedding. That is more appropriate than plain matrix factorization when preference relationships are nonlinear and history order matters.

The important product thesis is:

> A user can act as curator or explorer, and generation can be driven by interaction history rather than requiring the user to name every visual preference.

### 3.2 What Art Optimizer adopts

We adopt:

1. lightly prompted or unprompted exploration;
2. a persistent representation learned from previous interaction;
3. generation rather than catalog-only retrieval;
4. generated images re-entering the preference evidence stream;
5. artist-as-curator framing;
6. explicit concern about style monoculture and over-personalization.

### 3.3 What changes

We do not compress every interest into one average vector. Persistent taste is represented as a mixture:

$$
U=\{(u_k,\pi_k)\}_{k=1}^{K},
\qquad
\sum_k \pi_k=1.
$$

One possible utility is:

$$
m_u(I)=
\log\sum_{k=1}^{K}
\pi_k\exp\bigl(u_k^\top\phi(I)\bigr).
$$

An image can score highly by matching one coherent mode rather than weakly matching the average of incompatible modes.

Persistent taste is also distinct from current intent:

$$
w_t=w_{\mathrm{persistent}}+w_{\mathrm{session},t}.
$$

A new-world action resets the branch-local component but retains the persistent prior.

### 3.4 What the original work does not supply

It does not define a complete online policy for:

- which four images to show next;
- how uncertainty should drive exploration;
- how to construct a diverse slate rather than independently rank images;
- how to correct exposure and corner-position bias;
- how selection, star, reroll, history restoration, and reset differ;
- how to preserve exact generator state across a branch tree;
- how to optimize quantities along reusable directions;
- how a fast-changing local goal should override long-term taste.

Those are central Art Optimizer responsibilities.

## 4. Evan Shimizu: Design Adjectives and hover visualization

### 4.1 What it does

Shimizu studies parameterized design spaces whose low-level controls are difficult to navigate directly. The [Design Adjectives](https://graphics.cs.cmu.edu/projects/design-adjectives/) framework learns a user’s subjective function over bounded parameters from a small set of scored examples.

Given

$$
\mathcal D=\{(x_i,f_i)\}_{i=1}^{n},
\qquad f_i\in[0,1],
$$

it fits Gaussian-process regression with an anisotropic squared-exponential kernel:

$$
k(x,x')=
\exp\left[-\frac{1}{2}(x-x')^\top\Theta^{-2}(x-x')\right].
$$

Automatic relevance determination uses learned length scales to identify parameters that matter to the current subjective objective. The model guides interactive sampling and offers operations such as moving **Towards**, moving **Away**, finding designs with a **Similar Score**, and showing an **Axis** through the learned property.

Shimizu’s [Finding Layers Using Hover Visualizations](https://graphics.cs.cmu.edu/projects/hover-viz/) also demonstrates the value of temporarily seeing an item’s effect in full-resolution context before committing. This directly motivates corner hover/hold previews on the main Art Optimizer canvas.

### 4.2 What Art Optimizer adopts

We adopt:

1. a learned subjective function as a design control;
2. few-shot, branch-local fitting;
3. a continuous gallery-guided loop;
4. coarse-to-fine exploration;
5. parameter relevance as a route to future direction controls;
6. axis/sweep views for applying a direction in quantities;
7. full-context hover preview separated from commitment;
8. the pragmatic standard that the model need only help the user progress, not perfectly infer a timeless preference.

### 4.3 What changes

Shimizu’s implementation uses scalar ratings and primarily uses the GP mean. Art Optimizer should instead use comparative observations and exploit posterior uncertainty.

The user selects one item from a slate $S_t=\{a_{t1},\ldots,a_{t4}\}$ or selects the outside option $\varnothing$ by rerolling. A multinomial-logit likelihood is:

$$
P(y=j\mid S_t)=
\frac{\exp(f(a_{tj})/\tau)}
{\exp(b_t/\tau)+\sum_{k=1}^{4}\exp(f(a_{tk})/\tau)},
$$

$$
P(y=\varnothing\mid S_t)=
\frac{\exp(b_t/\tau)}
{\exp(b_t/\tau)+\sum_{k=1}^{4}\exp(f(a_{tk})/\tau)}.
$$

Here $b_t$ is a current acceptance threshold and $\tau$ captures judgment noise.

We also use uncertainty through an acquisition term such as:

$$
A(a)=\mu(a)+\beta\sigma(a),
$$

or by drawing candidate actions from posterior Thompson samples.

### 4.4 What the original work does not supply

It does not solve:

- deriving stable controls from a diffusion or flow model;
- distinguishing integer seeds from continuous initial-noise states;
- persistent and collaborative user priors;
- four-way slate acquisition with an outside option;
- nonstationary branch intent;
- event exposure correction;
- exact model-state replay;
- offline LoRA or preference fine-tuning.

## 5. Related work that fills the gap

### SwipeGANSpace

[SwipeGANSpace](https://arxiv.org/abs/2404.19693) combines PCA directions in StyleGAN space, swipe comparisons, preferential Bayesian optimization, and a UCB dimension-selection policy. It is a close precedent for lightweight visual feedback over learned directions. Its main limitation for this project is that it largely optimizes one discovered StyleGAN dimension at a time rather than a hybrid modern diffusion-control manifold.

### MultiBO

[MultiBO](https://arxiv.org/abs/2602.02388) is the closest recent precedent for multi-choice human feedback in a diffusion system. It presents several alternatives, receives a user selection, and performs preferential Bayesian optimization in a constrained self-attention transformation space. It strongly supports using multi-choice slates and attention-space controls instead of treating raw initial noise as the only search space.

### GimmBO

[GimmBO](https://arxiv.org/abs/2601.18585) performs preferential Bayesian optimization over mixtures of diffusion adapters. It is directly relevant to applying directions in different quantities:

$$
\theta(a)=\theta_0+\sum_{k=1}^{K}a_k\Delta\theta_k.
$$

Its difference from Art Optimizer is that GimmBO searches an existing adapter bank, while this project also aims to discover user-specific local directions and connect them to persistent preference.

### GANSpace and StyleCLIP

[GANSpace](https://arxiv.org/abs/2004.02546) and [StyleCLIP](https://arxiv.org/abs/2103.17249) establish the usefulness of interpretable directions and direction magnitude. Their controls are not, by themselves, learned from live personal browsing.

### FABRIC

[FABRIC](https://arxiv.org/abs/2307.10159) injects sets of positive and negative examples into diffusion attention without retraining. It suggests a practical route for using recent selected and rejected candidates as generation conditions while the optimizer decides which examples matter.

### DRaFT and Diffusion-DPO

[DRaFT](https://arxiv.org/abs/2309.17400) differentiates reward through diffusion sampling, while [Diffusion-DPO](https://arxiv.org/abs/2311.12908) learns from preferred/rejected image pairs. These belong in an offline consolidation loop after enough evidence accumulates, not in the click-by-click MVP.

## 6. Proposed mathematical model

### 6.1 Replayable design state

The authoritative design state is:

$$
s=(m,z,c,r,q,a),
$$

where:

- $m$ is exact model, precision, and sampler revision;
- $z$ is materialized initial noise or a content-addressed reference to it;
- $c$ is text and structural conditioning;
- $r$ is the set of reference images and weights;
- $q$ contains output and preservation constraints;
- $a$ is the cumulative action in the configured control manifold.

A candidate is produced by:

$$
I=G_\theta(s,a'),
$$

and its resulting state is an immutable child of $s$.

### 6.2 Persistent prior plus local residual

Let $m_u(I)$ score compatibility with persistent multi-interest taste and let $\delta_b(a)$ be a branch-local residual learned from recent choices:

$$
f_b(a)=
\lambda_t m_u\bigl(G(s_b,a)\bigr)+\delta_b(a).
$$

At a new world, $\lambda_t$ may be high because local evidence is scarce. As the user makes choices, the local posterior gains weight.

Use recency weighting or an explicit state-space model so a change of local goal is not treated merely as noisy labels:

$$
\mathcal L_t=
\sum_{s\le t}\gamma^{t-s}\ell_s,
\qquad 0<\gamma<1.
$$

### 6.3 Four-way slate acquisition

Do not independently return the four highest-scoring actions. Select a slate:

$$
S^*=\arg\max_{|S|=4}
\left[
\sum_{a\in S}\bigl(\mu(a)+\beta\sigma(a)\bigr)
+\lambda_D\log\det(K_S)
-\lambda_J\sum_{a\in S}D(a,a_0)
\right].
$$

The terms represent expected preference, uncertainty, slate diversity, and a controllable distance from the current anchor.

A practical quartet contains:

1. best local continuation;
2. best diverse continuation;
3. informative uncertainty probe;
4. controlled surprise or another persistent interest mode.

### 6.4 Reroll

Reroll is the outside-option observation $y=\varnothing$. Give it less weight than a positive selection unless the user explicitly chooses “dislike all.” Repeated rerolls widen the local trust region or increase exploration pressure while retaining the current design and root noise.

### 6.5 Event semantics

| Event | Local model | Persistent model |
|---|---|---|
| Select candidate | strong comparative positive | small positive |
| Star | optional positive | very strong positive |
| Reroll | weak outside-option evidence | normally none |
| Restore old design | reopen prior branch | moderate revisit evidence |
| Export | moderate positive | extremely strong positive |
| New world | reset local posterior | preserve prior |
| Hover/hold | no preference update in MVP | none |

The selection should be modeled as one four-way choice, not blindly expanded into three independent pairwise labels.

## 7. Seed and initial-noise space

### 7.1 Integer seed adjacency is meaningless

A PRNG seed is a discrete recipe for producing a tensor. Seed $n+1$ is not a nearby image to seed $n$. Never define a direction by adding numbers to the integer seed.

### 7.2 Materialized noise is continuous

Initial noise is a tensor $z_0\in\mathbb R^N$. A local direction is meaningful:

$$
z(\alpha)=z_0+\alpha d_z.
$$

A norm-preserving correlated variation is often better:

$$
z'=\rho z_0+\sqrt{1-\rho^2}\,\epsilon,
\qquad \epsilon\sim\mathcal N(0,I).
$$

Interpretation:

- $\rho\approx1$: small stochastic variation;
- moderate $\rho$: broader structural variation;
- $\rho=0$: independent new world.

### 7.3 MVP policy

Fix the exact materialized noise tensor within one world while testing semantic, reference, adapter, and attention controls. A new-world action draws a new tensor. Later experiments may add a small bounded low-dimensional noise subspace.

Occasional factorial slates can separate a preference for a control direction from a lucky random realization:

```text
A1 = direction A, noise variant 1
A2 = direction A, noise variant 2
B1 = direction B, noise variant 1
B2 = direction B, noise variant 2
```

## 8. Learning directions and quantities

Let $\phi(I)$ combine semantic, style, composition, quality, artifact, and action features.

A regularized preference direction in feature space is:

$$
d_\phi=(\Sigma_\phi+\lambda I)^{-1}
(\bar\phi_+-\bar\phi_-).
$$

To pull it back into generator controls, estimate the local Jacobian:

$$
J(a)=\frac{\partial\phi(G(s,a))}{\partial a}.
$$

Then solve:

$$
d_a=\arg\min_d
\|Jd-d_\phi\|_W^2+\lambda\|d\|^2,
$$

with ridge solution:

$$
d_a=(J^\top WJ+\lambda I)^{-1}J^\top Wd_\phi.
$$

Numerically orthogonal controls may still be visually redundant. Define a perceptual metric:

$$
M(a)=J(a)^\top WJ(a)+\epsilon I,
$$

and seek directions satisfying approximately:

$$
d_i^\top M d_j=\delta_{ij}.
$$

Raw coefficients are rarely perceptually linear. Parameterize displayed quantity by perceptual arclength:

$$
s(\alpha)=
\int_0^\alpha
\sqrt{d^\top M(a_0+td)d}\,dt.
$$

Sample a sweep, fit a monotone map, and expose equal increments in $s$, not raw $\alpha$.

Each stored direction needs scope metadata: model revision, anchor/world, conditioning context, control space, valid radius, and supporting evidence.

## 9. Bandit first, RL later

The first product is a contextual preferential bandit or sequential Bayesian optimizer:

- context: current design, branch history, and persistent interest modes;
- action: a slate of four control actions;
- observation: one selected candidate or reroll;
- immediate outcomes: selection, star, revisit, export.

Full reinforcement learning becomes useful only for genuinely long-horizon decisions: when to challenge current taste, when to reset, how novelty changes later goals, or how to trade convergence against discovery.

Do not optimize raw dwell time as the primary reward. It is confounded by loading, confusion, shock, and distraction, and encourages engagement optimization rather than creative progress.

## 10. Model substrate survey

### 10.1 Default research target: FLUX.2 [klein] 4B

Black Forest Labs describes [FLUX.2 \[klein\] 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) as a four-billion-parameter rectified-flow model with text-to-image, editing, and multi-reference support. The distilled checkpoint uses four inference steps and is Apache 2.0. Its open weights and unified generation/editing surface make it the leading default substrate for the first implementation.

Vendor performance claims must be reproduced on project hardware before they become project benchmarks.

### 10.2 Krea 2 Turbo

[Krea 2](https://github.com/krea-ai/krea-2) is explicitly oriented toward creative and stylistic exploration. Turbo is an eight-step distilled model, and Krea recommends training LoRAs on Raw and applying them to Turbo. That Raw-to-Turbo path is attractive for later offline preference consolidation. License and product-fit diligence remain necessary.

### 10.3 SANA-Sprint

NVIDIA’s [SANA-Sprint](https://research.nvidia.com/labs/eai/publication/sana-sprint/) supports one-to-four-step generation and ControlNet and is an important extreme-throughput benchmark. Its usefulness depends on checkpoint licensing, edit continuity, and measured quality under the project’s real prompts.

### 10.4 Renderer abstraction

The model choice is provisional. A renderer adapter declares:

- supported generation and edit modes;
- deterministic replay guarantees;
- available control spaces;
- reference and adapter support;
- license and policy requirements;
- hardware and precision constraints;
- measured latency and batch behavior.

## 11. Evaluation

### Preference learning

Measure:

- held-out four-way choice log likelihood;
- calibration and uncertainty quality;
- simulated-user regret;
- interactions until first star or export;
- robustness to changing preference modes.

### Candidate slates

Measure:

- within-slate perceptual diversity;
- duplicate rate;
- selection rate by proposal role;
- reroll rate;
- exposure effects by slot;
- information gained per round;
- time until first and fourth usable candidate.

### Direction quality

Measure:

- monotonicity across quantities;
- identity and content preservation;
- semantic leakage;
- local validity radius;
- cross-seed, cross-world, and cross-parent transfer;
- interference between directions;
- perceptual linearity of increments.

### Product success

Measure creative progress rather than only engagement:

- sessions producing a favorite or export;
- rounds until a satisfactory design;
- meaningful forks and revisits;
- ability to recover from a poor branch;
- selected-output diversity;
- explicit surprise/usefulness ratings;
- long-term retention without aesthetic collapse.

## 12. Initial experiment matrix

| Experiment | Variable | Baseline | Primary outcome |
|---|---|---|---|
| Fixed vs varied noise | same root vs correlated noise | independent seeds | choice consistency and convergence |
| Four-way policy | role-balanced slate | top four predicted | reroll rate and utility gain |
| Preference model | Bayesian linear vs PairwiseGP | running centroid | held-out choice likelihood |
| Control space | noise vs conditioning vs hybrid | prompt-only | utility gain per render |
| Persistent prior | none vs centroid vs multi-interest | no history | new-world cold start |
| Preview UI | corner hover vs visible 2×2 grid | thumbnails only | confidence and selection time |
| Reroll update | weak outside option | strong all-negative | recovery and stability |
| Direction quantity | perceptual calibration | raw coefficient | monotonicity and control |

## 13. Open questions

1. Which control manifold gives the best preference-learning efficiency?
2. How stable are directions across roots, prompts, and model revisions?
3. How much fixed noise improves attribution before it harms diversity?
4. Should ordinary branch selection update persistent taste, or only revisit/star/export?
5. How should persistent interest modes influence a branch without collapsing every world toward the same aesthetic?
6. Which four-way acquisition policy best balances useful convergence and discovery?
7. Can the model detect a changed local goal rather than treating it as inconsistent labels?
8. How should reroll update acceptance threshold versus the utility surface?
9. Do low-resolution judgments predict preferences over final renders?
10. When does offline LoRA/DPO consolidation improve efficiency, and when does it collapse diversity?
11. How can authorship, surprise, and creative agency be evaluated without reducing them to engagement?

## 14. References

Primary inspirations:

- Ryan Murdock. [Generative Recommenders](https://rynmurdock.github.io/writing/generative_recommenders.html), 2024; revisions through 2025.
- Ryan Murdock. [Preference Prior](https://github.com/rynmurdock/preference-prior), 2025.
- Evan Shimizu. [Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools](https://www.evanshimizu.com/port/CMU-CS-20-104.pdf), CMU-CS-20-104, 2020.
- Evan Shimizu et al. [Design Adjectives](https://graphics.cs.cmu.edu/projects/design-adjectives/), UIST 2020.
- Evan Shimizu et al. [Finding Layers Using Hover Visualizations](https://graphics.cs.cmu.edu/projects/hover-viz/), Graphics Interface 2019.

Interactive preference optimization:

- Nakashima, Yang, and Baba. [SwipeGANSpace](https://arxiv.org/abs/2404.19693), 2024.
- Rajagopalan et al. [MultiBO](https://arxiv.org/abs/2602.02388), 2026.
- Liu, Ling, and Jacobson. [GimmBO](https://arxiv.org/abs/2601.18585), 2026.
- Chu and Ghahramani. [Preference Learning with Gaussian Processes](https://www.cs.cornell.edu/people/tj/publications/chu_ghahramani_05a.pdf), 2005.
- González et al. [Preferential Bayesian Optimization](https://proceedings.mlr.press/v70/gonzalez17a.html), 2017.
- [BoTorch preference-learning tutorial](https://botorch.org/docs/tutorials/preference_bo/).

Generative controls and adaptation:

- Härkönen et al. [GANSpace](https://arxiv.org/abs/2004.02546), 2020.
- Patashnik et al. [StyleCLIP](https://arxiv.org/abs/2103.17249), 2021.
- von Rütte et al. [FABRIC](https://arxiv.org/abs/2307.10159), 2023.
- Clark et al. [DRaFT](https://arxiv.org/abs/2309.17400), 2023.
- Wallace et al. [Diffusion-DPO](https://arxiv.org/abs/2311.12908), 2023.

Candidate model families:

- Black Forest Labs. [FLUX.2 \[klein\] release](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence) and [4B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), 2026.
- Krea AI. [Krea 2](https://github.com/krea-ai/krea-2), 2026.
- Chen et al. [SANA-Sprint](https://research.nvidia.com/labs/eai/publication/sana-sprint/), 2025.
