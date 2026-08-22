# Research Review 2/5: Evan Shimizu's Design Adjectives

**Primary objects reviewed**

- Evan Shimizu, Matthew Fisher, Sylvain Paris, James McCann, and Kayvon Fatahalian. [“Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces.”](https://doi.org/10.1145/3379337.3415866) UIST 2020, pp. 261–278.
- Evan Shimizu. [*Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools*](https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf). CMU-CS-20-104, 2020.
- [`ebshimizu/DesignAdjectives`](https://github.com/ebshimizu/DesignAdjectives), released implementation.
- [Official project page](https://graphics.cs.cmu.edu/projects/design-adjectives/).

**Source status:** peer-reviewed UIST paper, doctoral thesis, project page, source code, user study, and professional case studies.

## 1. Review question

What does Design Adjectives establish about interactive exploration of a high-dimensional subjective design space, and which parts transfer cleanly to generative image optimization?

The central answer is:

> A user can iteratively teach a lightweight subjective function from a few visual judgments, then use that model to guide gallery sampling while retaining access to lower-level parameters for refinement.

This is the clearest prior foundation for Art Optimizer's **branch-local design loop**.

## 2. The design problem

Shimizu begins from a common mismatch. A parametric design may be represented by tens or hundreds of low-level variables, while the designer's goal is expressed at a much higher level:

```text
low-level controls
    stroke width, roughness, particle speed, brick count, spacing, scale...

subjective intent
    elegant, dense, energetic, shiny, playful, restrained...
```

A slider panel exposes the implementation's degrees of freedom, not the structure of the user's current intent. A static gallery exposes variety, but is difficult to steer toward a changing goal.

Design Adjectives combines:

1. a bounded parameterized design space;
2. user-scored examples;
3. a learned subjective function;
4. guided sampling modes;
5. a gallery for rapid visual judgment;
6. parameter-level tools for final refinement.

The framework is explicitly coarse-to-fine. Sampling helps locate promising regions; low-level tools remain available for detail work.

## 3. Formal model

Let the design space be:

\[
\mathcal X \subset \mathbb R^d,
\]

with labeled examples:

\[
\mathcal D
=\{(x_i,f_i)\}_{i=1}^{n},
\qquad f_i\in[0,1].
\]

The user's scalar score defines a subjective design adjective. Shimizu's domain-agnostic implementation fits Gaussian process regression:

\[
f(x) \sim \mathcal{GP}(m(x), k(x,x')).
\]

The thesis presents an anisotropic squared-exponential kernel with per-parameter length scales:

\[
k(x,x')
=\exp\left[-\frac{1}{2}(x-x')^\top\Theta^{-2}(x-x')\right].
\]

The diagonal elements of \(\Theta\) act as automatic relevance determination: short learned length scales indicate that the subjective score changes quickly along a parameter, while long scales imply lower sensitivity.

Given observed scores \(f\), the GP posterior mean at \(x_*\) is the familiar:

\[
\mu(x_*)
=k(X,x_*)^\top K(X,X)^{-1}f,
\]

with standard extensions for observation noise and learned hyperparameters.

### 3.1 Why a GP fits the setting

The thesis motivates GPR because it can:

- fit from very few examples;
- update quickly enough for interactive use;
- represent nonlinear parameter interactions;
- expose parameter relevance through length scales;
- provide a smooth subjective surface over a bounded design space.

The implementation uses GPyTorch and a client/model/communication-server architecture in the released repository.

### 3.2 What the implementation does with uncertainty

A Gaussian process supplies both mean and posterior uncertainty. The Design Adjectives implementation primarily uses the **mean** as the adjective score that drives acceptance criteria. Its sampler is not framed as an information-gain or upper-confidence-bound acquisition policy.

This matters for Art Optimizer. Shimizu supplies the learned subjective surface and interaction philosophy, but uncertainty-aware next-query selection comes from preferential Bayesian optimization and active-learning literature.

## 4. Guided rejection sampling

Design Adjectives samples proposals in parameter space and accepts them when they satisfy a mode-specific criterion and a minimum difference threshold. The threshold prevents the gallery from simply recycling near-identical or already-labeled designs.

The four modes are unusually relevant.

### 4.1 Towards

Generate designs whose predicted adjective score is higher than the current design:

\[
\mu(x') > \mu(x).
\]

Use case: move toward a stronger expression of the current preference or toward a likely final design.

### 4.2 Away

Generate designs with a lower adjective score:

\[
\mu(x') < \mu(x).
\]

Use case: refine what the adjective means, escape a local basin, or deliberately surface variety outside known-good examples.

The label “Away” is important. Exploration is not only uncertainty near the optimum; sometimes a designer wants to challenge the current definition.

### 4.3 Similar Score

Generate designs whose predicted score is within a tolerance of the current design:

\[
|\mu(x')-\mu(x)| \leq \epsilon.
\]

The thesis uses a tolerance around ten percent in its implementation. Crucially, similar score does not mean visually or parametrically similar. It means “a comparable amount of the learned subjective property.”

This is a direct precedent for Art Optimizer's proposed command:

> Equally appealing, structurally different.

### 4.4 Axis

Generate examples regularly spaced along the learned adjective scale. This provides a visual sweep of how the learned concept manifests across the design domain.

The word “Axis” refers to the scalar learned adjective score. It does not mean that the sampler follows one linear parameter-space direction \(x_0+td\). The released sampler seeks designs at separated predicted-score levels while mutating subsets of parameters.

A linear `-2d, -d, current, +d, +2d` sweep may still be useful for Art Optimizer, but it is our control-basis diagnostic, not an operation established by Shimizu.

## 5. Interface contribution

The evaluated interface places the current design in a large view, shows sampled suggestions in a gallery, and allows hovering a thumbnail to render it in the main view. Parameter controls remain accessible.

This establishes several interaction principles.

### 5.1 Full-context preview

Small thumbnails are useful for scanning, but judgments often require the design's full context. Hovering a suggestion temporarily displays it at full size without immediately changing the current design.

Art Optimizer's distinction follows directly:

```text
preview
    temporary display, no branch mutation

commit
    explicit state transition and preference observation
```

### 5.2 Coarse-to-fine tools

The model-guided gallery does not replace all direct manipulation. The thesis uses adjective-derived information to:

- highlight influential parameter sliders;
- visualize parameter extents;
- mix designs;
- and help users decide which controls matter for final edits.

The broader lesson is that recommendation and direct control are complements. Art Optimizer should initially hide complex controls, but learned axis sweeps and preservation locks can become refinement tools once the basic browse-and-choose loop works.

### 5.3 Mobile preview precedent

The thesis's future-interface discussion sketches swipe-based rating, rated-design history, and press-and-hold full-size preview on mobile. This is relevant precedent for touch interaction, but it was proposed as an adaptation, not the principal evaluated mobile interface. It should be cited as future design discussion rather than user-study evidence.

## 6. Evaluation evidence

The project demonstrates the framework in:

- parametric materials;
- parametric fonts;
- particle systems.

The paper and thesis report a user study and professional case studies. The official project abstract says participants could explore and find designs they liked, and professional cases demonstrate concepting workflows. The thesis reports that users generally felt exploration was quicker and easier than with existing per-parameter interfaces.

The evaluation provides evidence for:

- the usability of model-guided galleries;
- few-example subjective-function learning;
- interactive update rates in the tested parameter spaces;
- value across more than one design domain;
- the usefulness of maintaining low-level access.

It does not directly establish:

- effectiveness in a modern diffusion-transformer control space;
- pairwise or multi-choice preference likelihoods;
- long-term preference memory;
- collaborative personalization;
- robustness to generated-image artifacts;
- or optimal gallery size.

## 7. What transfers to Art Optimizer

### Directly adopted

1. **One current design plus generated alternatives.**
2. **A learned subjective function guides local exploration.**
3. **Few-shot, interactive updates are more important than asymptotic model capacity.**
4. **Full-size preview should not imply commitment.**
5. **Sampling should avoid trivial near-duplicates.**
6. **Different exploration intents require different proposal modes.**
7. **An axis sweep is both a navigation and interpretation tool.**
8. **Approximate models are acceptable when the interaction loop lets the user correct them.**
9. **Exploration and detailed direct manipulation belong to different phases.**

### Modified by Art Optimizer

#### Scalar scores become discrete choices

Shimizu observes absolute ratings:

\[
f_i\in[0,1].
\]

Art Optimizer's main interface observes one choice among the anchor and exposed candidates:

\[
y_t\in\{0,1,\ldots,m\},
\]

where \(y_t=0\) means an explicit `NoneOfThese`/anchor preference and \(y_t=j\) means candidate \(j\) was committed. A neutral `MoreVariety` request is not a choice observation.

This reduces calibration burden. Users usually find “which is better?” easier and more consistent than assigning a stable score such as 0.73.

#### GP mean sampling becomes uncertainty-aware acquisition

Art Optimizer wants candidates that jointly include:

- likely improvement;
- another plausible posterior direction;
- an informative probe;
- controlled surprise.

That requires posterior uncertainty and slate diversity, not only score-threshold rejection.

#### Explicit parameters become a model codec

Design Adjectives assumes a declared bounded parameterization. Diffusion systems do not naturally provide one clean semantic space. Art Optimizer therefore treats the codec/control basis as an experimental object that must be versioned and validated.

#### One adjective originally became persistent plus local structure

The original Art Optimizer synthesis added a persistent multimodal taste atlas across sessions and a fast branch-local posterior for the current project. Round 1 showed that this becomes incoherent when those layers maintain unrelated preference representations. The current architecture decision is instead one versioned family of taste components with branch-local activation and immutable history; see [One Authoritative Taste State](14_ONE_AUTHORITATIVE_TASTE_STATE_REVIEW.md).

## 8. Important limitations

### 8.1 Scalar-rating burden

Absolute ratings assume users can maintain a meaningful numeric scale across examples and time. Ratings can drift, compress, or depend on context. Multi-choice observations avoid some of this burden but sacrifice score magnitude.

### 8.2 Explicit bounded design space

The framework is strongest when every sample corresponds to a stable parameter vector. A modern image generator may expose prompt embeddings, attention interventions, adapter weights, references, and noise variables with different geometry and transfer properties.

### 8.3 Mean-driven sampling

Using only the GP mean leaves information-gain opportunities unused. A system may repeatedly exploit a model that is confidently wrong because it never deliberately probes uncertain regions.

### 8.4 Stationary subjective function

The user's goal can change after seeing an unexpected design. A single stationary function may treat inspiration-driven drift as inconsistent noise.

### 8.5 Gallery scale and fatigue

The framework establishes the value of galleries but does not settle the ideal number of alternatives for Art Optimizer's full-image, low-latency setting. Four is a product hypothesis, not a theorem inherited from Design Adjectives.

### 8.6 Parameter relevance is local and model-dependent

ARD length scales can suggest important parameters, but “important” means influential under the learned function and observed region. It does not guarantee a globally semantic or disentangled control.

## 9. Design implications

### 9.1 Keep the local learner small

The product does not initially need a giant neural reward model. Shimizu's work supports starting with a data-efficient probabilistic model that can be updated after every choice.

### 9.2 Preserve a current anchor

The current design is a meaningful reference, not merely the last item in a feed. Every quartet should answer:

> Which candidate, if any, is worth replacing this design with?

### 9.3 Introduce exploration modes as planner roles first

The system can implement analogues of Towards, Similar Score, Away, and Axis internally before exposing them as buttons:

| Design Adjectives | Art Optimizer internal role |
|---|---|
| Towards | best local continuation |
| Similar Score | diverse posterior candidate with comparable predicted utility |
| Away | controlled surprise / basin escape |
| Axis | gallery spread across separated scalar adjective-score levels; using utility levels is Art Optimizer's adaptation |

An explicit linear direction sweep is a separate Art Optimizer control-basis experiment. This keeps the source attribution precise while preserving the richer design logic.

### 9.4 Build refinement only after exploration works

Learned sliders, direction chips, locks, and axis sweeps are valuable, but they should emerge after the four-choice loop can reliably find useful regions.

## 10. Evaluation agenda derived from Shimizu

1. **Few-shot learning:** how many choices before candidates improve over random/local baselines?
2. **Interactive latency:** can the model update and propose before rendering becomes the bottleneck?
3. **Exploration coverage:** do users see broader useful regions than with direct sliders or random seed browsing?
4. **Recovery:** can users escape a poor local basin without losing the current design?
5. **Refinement transfer:** do learned directions or relevance estimates make later direct controls easier?
6. **Model correction:** how quickly does the system recover after a misleading selection?
7. **Cross-domain behavior:** do results hold for portraits, abstract art, graphic design, architecture, and material-like imagery?

## 11. Citation-safe conclusion

The strongest citation-safe statement is:

> Shimizu et al.'s Design Adjectives framework shows that a Gaussian-process model of user-scored examples can guide interactive gallery exploration in high-dimensional parameterized design spaces, with sampling modes for seeking higher scores, lower scores, similar scores, or separated levels of the learned scalar adjective score. Art Optimizer adapts this local design-search pattern to multi-choice feedback over image-generator controls, adds uncertainty-aware acquisition, and proposes branch-local activation within one persistent versioned taste state.

Art Optimizer should not imply that Design Adjectives validates diffusion latent directions, four-candidate slates, persistent user priors, or the current multinomial learner.

## References

- Evan Shimizu, Matthew Fisher, Sylvain Paris, James McCann, and Kayvon Fatahalian. [“Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces.”](https://doi.org/10.1145/3379337.3415866) UIST 2020, 261–278.
- Evan Shimizu. [*Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools*](https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf). Carnegie Mellon University, 2020.
- [Design Adjectives project page](https://graphics.cs.cmu.edu/projects/design-adjectives/).
- [`ebshimizu/DesignAdjectives`](https://github.com/ebshimizu/DesignAdjectives).
- Carl Edward Rasmussen and Christopher K. I. Williams. [*Gaussian Processes for Machine Learning*](https://gaussianprocess.org/gpml/). MIT Press, 2006.
