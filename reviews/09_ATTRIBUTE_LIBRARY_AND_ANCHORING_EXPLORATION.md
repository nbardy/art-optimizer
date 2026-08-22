# From Image Anchors to Composable Concept Lanes

**Status:** conceptual exploration and executable UI hypothesis  
**Date:** 2026-08-22  
**Question:** should Art Optimizer treat the current image as the thing being optimized, or as one temporary rendering of a reusable composition of learned visual directions?

## Abstract

Art Optimizer v0 uses a simple and defensible local interaction: one committed image is the outside option, four nearby alternatives are shown, and the user either chooses one or keeps the current image. This gives clean discrete-choice data and preserves continuity, but it also risks turning the current image into an accidental bottleneck. A desirable visual attribute may be discovered in one branch, lost during another improvement, and difficult to recover except by restoring the entire old image.

This note separates four objects that v0 partially conflates:

1. **the current realization** — one image generated from one seed and action;
2. **the concept composition** — a set of reusable, weighted, independently activatable directions;
3. **the branch-local preference posterior** — what appears useful during the present exploration;
4. **the persistent taste atlas** — durable regions and exemplars that tend to matter across worlds.

The proposed extension learns unnamed concept lanes from accepted action deltas, weakly revises them after exposed rerolls, automatically activates or mutes them, and allows the user to recast the active composition under a new stochastic seed. Three interface designs explore how much of this structure should be visible: implicit lanes, a visible concept shelf, and a lane-organized candidate board.

The central claim is not that image anchoring is wrong. The claim is that **comparison anchor, proposal center, concept memory, and stochastic realization should be distinct variables**.

## 1. The strength and limitation of the current design

The current round has an anchor action \(a_t\), four candidate actions \(a_{t1},\ldots,a_{t4}\), and one multinomial observation. The current image is alternative zero:

\[
P(y_t=j)
=
\frac{\exp(f(a_{tj})/\tau)}
{\exp(f(a_t)/\tau)+\sum_i\exp(f(a_{ti})/\tau)}.
\]

Reroll means \(y_t=0\): none of the meaningfully exposed candidates was preferred to the committed image. This remains an excellent interpretation of the immediate user action.

The problem appears when this local comparison object is also treated as the only durable description of intent. Suppose a user discovers:

- a translucent material treatment;
- a sparse radial composition;
- a peculiar turbulent edge structure;
- and an unusual color relation.

Those discoveries may occur in different images. Restoring an image recovers all of its properties together, including properties the user no longer wants. A single-image anchor therefore couples attributes that should sometimes be independently reusable.

The image is a good **outside option**. It is not necessarily the best **memory representation**.

## 2. Four kinds of state

We propose the following decomposition.

### 2.1 Realization state

A rendered design is:

\[
x = G_\theta(z,c,a),
\]

where \(z\) is the materialized stochastic root, \(c\) is the fixed world condition, and \(a\) is an absolute action in the versioned model control basis.

The committed image remains authoritative for:

- what the user is currently viewing;
- the outside option in the next choice;
- replay and history;
- branch continuity;
- explicit favorite and export operations.

### 2.2 Concept-composition state

A concept lane is not an image. It is a reusable local transformation hypothesis:

\[
C_k=(d_k,m_k,\alpha_k,s_k^+,s_k^-,q_k,\mathcal S_k).
\]

- \(d_k\): normalized direction in a declared control basis;
- \(m_k\): typical accepted magnitude;
- \(\alpha_k\): user-adjustable amount;
- \(s_k^+\), \(s_k^-\): positive and negative evidence;
- \(q_k\in\{\text{auto},\text{on},\text{off}\}\): activation policy;
- \(\mathcal S_k\): scope and provenance, including model and basis revision.

The concept may be unnamed. `Lane 3` is preferable to a confident but false semantic label. A language model or VLM can later propose a name from exemplars and axis sweeps, but naming is downstream of the learned control object.

### 2.3 Branch-local preference state

The current Bayesian choice posterior remains responsible for immediate utility and uncertainty. It answers:

> Given this world and recent choices, which candidate actions are promising now?

It should adapt rapidly and may forget. It is not required to preserve every reusable concept forever.

### 2.4 Persistent taste state

The Murdock-inspired persistent atlas answers a different question:

> Which visual regions, exemplars, and modes have repeatedly mattered across sessions and worlds?

The atlas stores regions or modes. The concept library stores transformations or attributes. A mode might be “dark translucent architectural forms”; a concept lane might be “increase translucent material while preserving the rest.” They should not be forced into one representation.

## 3. Learning a non-prompt concept lane

The executable experiment uses accepted action deltas. When candidate \(j\) is selected over anchor \(a_t\):

\[
\delta_t=a_{tj}-a_t,
\qquad
\hat d_t=\frac{\delta_t}{\|\delta_t\|}.
\]

The observation is matched to an existing lane by cosine similarity:

\[
k^*=\arg\max_k d_k^\top\hat d_t.
\]

When similarity exceeds a merge threshold, update that direction and its characteristic magnitude online. Otherwise, create a new lane. The current prototype uses a conservative threshold of 0.82 and caps each control-basis scope at twelve lanes.

A weighted directional update is:

\[
d_k'=\operatorname{normalize}\left(s_k^+ d_k + \hat d_t\right),
\]

\[
m_k'=\frac{s_k^+m_k+\|\delta_t\|}{s_k^++1}.
\]

This is deliberately simple. It is an online clustering baseline, not a claim that accepted deltas form von Mises–Fisher clusters or globally stable semantic axes.

### 3.1 Negative evidence

A reroll is weak negative evidence only when at least two candidates were meaningfully exposed. For an existing concept direction \(d_k\), compute its maximum alignment with the rejected candidate deltas. A sufficiently aligned concept receives a small opposition update.

This remains deliberately weaker than positive evidence because reroll can mean:

- wrong amount;
- wrong interaction with another attribute;
- bad stochastic realization;
- uninteresting slate;
- temporary branch intent;
- or actual dislike of the direction.

A generic thumbs-down would collapse these explanations even more aggressively.

### 3.2 Automatic activation

The current experiment uses a transparent score:

\[
r_k=s_k^+-s_k^-.
\]

In `auto` mode, a lane is active when \(r_k\) exceeds a threshold. The user may force it on or off. A mature implementation should use hysteresis:

\[
q_k=\begin{cases}
\text{on}, & r_k>\tau_{\mathrm{on}},\\
\text{off}, & r_k<\tau_{\mathrm{off}},\\
q_k^{\mathrm{previous}}, & \text{otherwise},
\end{cases}
\qquad
\tau_{\mathrm{off}}<\tau_{\mathrm{on}},
\]

so small fluctuations do not make attributes flicker between states.

## 4. Composing concepts independently of the current image

Let \(S\) be the active concept set. The experiment forms a composition action:

\[
a_C=\Pi_{\mathcal A}\left[b+\frac{1}{\sqrt{|S|}}\sum_{k\in S}\alpha_k m_k \gamma_k d_k\right],
\]

where \(b\) is a chosen basis origin, \(\gamma_k\) is a confidence attenuation, and \(\Pi_{\mathcal A}\) clips or projects into the valid action domain.

The executable client currently uses \(b=0\), a confidence floor, square-root normalization, and clipping to \([-0.9,0.9]^d\). This is intentionally different from continuing from the current action. It asks:

> What does the learned concept composition produce when rendered as its own object?

A **recast** samples a new stochastic root while retaining this action:

\[
x'=G_\theta(z',c,a_C),\qquad z'\sim p(z).
\]

That operation separates a reusable non-prompt composition from the accidents of one seed.

## 5. The image anchor and concept anchor can coexist

There are at least three centers in an interactive round:

1. **comparison anchor** \(a_t\): the committed image, used as the outside option;
2. **proposal center** \(b_t\): where the planner samples candidate actions;
3. **composition center** \(a_C\): the action implied by active reusable concepts.

They need not be equal.

A future planner may use:

\[
b_t=(1-\rho_t)a_t+\rho_t a_C,\qquad 0\le\rho_t\le1,
\]

while still comparing every candidate against the actual current image in the likelihood. This lets the system preserve a truthful user query while gradually pulling proposals toward the concept composition.

Other useful proposal roles are local around the current realization, local around the active concept composition, crossover between active and inactive lanes, and orthogonal discovery unexplained by the library.

The present implementation does not yet replace the server planner center. It implements concept learning, concept-aware classification, and composition recasting first, so the interaction hypotheses can be tested before changing the inference core.

## 6. Relationship to Design Adjectives

Shimizu's Design Adjectives treats a parameterized design space as the domain of a learned subjective function and exposes guided operations such as Towards, Away, Similar Score, and Axis. The important lesson is not that every user must manipulate model parameters directly. It is that a learned subjective model can support several qualitatively distinct design operations rather than only “give me the next best sample.”

The concept-lane extension translates that idea as follows:

| Design Adjectives operation | Concept-lane interpretation |
|---|---|
| Towards | strengthen or force on a learned lane |
| Away | mute a lane or apply its negative direction |
| Similar Score | preserve active concept composition while changing seed or unexplained coordinates |
| Axis | render a calibrated sweep through one lane |
| affected parameters | expose which codec coordinates or learned controls carry the lane |
| guided gallery | organize alternatives by active, alternate, and discovery lanes |

The extension differs in two ways. First, the parameter directions themselves may be learned rather than named in advance. Second, the user is not required to rate a scalar adjective; concepts emerge from ordinary selections and may remain unnamed.

## 7. Relationship to Murdock's preference representation

Murdock's Generative Recommenders demonstrates a bridge from interaction history to generative conditioning, first through visually aligned collaborative factors and later through a sequence-conditioned preference-prior experiment. This motivates preserving preference in a generatively actionable representation rather than merely ranking a catalog.

Concept lanes are a complementary representation:

```text
persistent taste atlas
    which regions or modes matter?

concept library
    which reusable changes or attributes matter?

branch posterior
    which immediate move is useful now?
```

The library should eventually be persistent and potentially collaborative, but its control vectors must remain scoped to compatible model and control-basis revisions. A FLUX direction and a Krea direction may share a human interpretation without sharing numeric coefficients.

## 8. User-action burden

The largest design risk is exposing a miniature node editor before the user has made anything.

The proposed principle is:

> Learn implicitly, reveal progressively, allow explicit override, and keep the primary loop intact.

The minimum primary actions remain:

```text
choose one
reroll
favorite
new world
history
```

Concept operations can be layered.

### Level 0 — invisible automation

Selections create or reinforce lanes. Rerolls weakly oppose them. The system uses them for recasting or proposal diversity without asking for extra input.

### Level 1 — one composition action

Expose only `Recast learned mix`. This is the strongest low-burden addition: keep what I have taught you, change the image realization.

### Level 2 — optional tri-state chips

An advanced drawer exposes `AUTO / ON / OFF` and amount. The default remains automatic. Explicit action is corrective rather than mandatory.

### Level 3 — concept workbench

A research or expert interface may expose axis sweeps, naming, merging, splitting, crossovers, scope, and provenance. This should not be the default creative flow.

## 9. Four design alternatives

### Baseline: current-image evolution

One full canvas, four corner descendants, and a current-image outside option.

**Strengths:** minimal, continuous, clear, easy to learn.  
**Risk:** desired attributes remain entangled with one image.

### Attempt A: implicit lanes

The original visual grammar remains. Concept learning is automatic and mostly hidden. A small status element reveals that lanes exist; a drawer permits intervention; one prominent action recasts the active composition.

**Hypothesis:** gains reusable intent with minimal additional cognitive load.  
**Risk:** hidden automation may feel magical or inexplicable.

### Attempt B: concept shelf

The current image and four candidates remain primary, but an always-visible shelf shows learned lanes with exemplar, evidence, tri-state activation, and strength.

**Hypothesis:** makes composition legible and controllable without requiring formal prompts.  
**Risk:** converts browsing into parameter management and encourages premature micromanagement.

### Attempt C: lane board

Candidates are grouped by relation to the concept library: active composition, alternate learned lane, or discovery not explained by the library.

**Hypothesis:** the candidate set itself teaches the user what has been learned and preserves exploratory diversity.  
**Risk:** moving candidates between semantic groups introduces layout complexity and can bias judgments through labels.

## 10. Failure modes

### False concepts

A selected delta may reflect a lucky seed-specific detail rather than a reusable attribute. Countermeasures include repeated evidence, factorial seed probes, transfer tests, and conservative promotion.

### Entangled concepts

Two directions may carry the same perceptual effect or one direction may change several things. Future work should use local Jacobians and perceptual metrics to merge redundant lanes or split unstable ones.

### Concept proliferation

Every selection could create a lane. The prototype uses similarity merging and a hard cap; a mature system should add minimum support, dormancy, merge/split operations, and scope-aware forgetting.

### Negative-evidence ambiguity

Reroll may reject the amount or realization rather than the direction. Negative updates must remain weak and reversible.

### Model-transfer error

A lane is numeric only within its declared basis. Cross-model transfer must happen through visual exemplars or a learned transport map, never by blindly copying coefficients.

### Automation surprise

Automatic on/off changes can make the system feel inconsistent. Interfaces must show the active composition, provide undo/restore, and permit forced overrides.

### Composition collapse

Adding many positive concepts can saturate controls. Normalization, bounds, sparsity, and incompatibility checks are required.

## 11. Evaluation questions

The three interfaces should be compared on:

- time and choices to first export-worthy image;
- ability to recover a desired attribute after changing the image;
- success when recasting a composition under new seeds;
- number of explicit concept operations per session;
- user understanding of commit versus favorite versus concept activation;
- perceived authorship and control;
- diversity of selected outputs;
- concept transfer across prompts and seeds;
- false-lane rate and concept proliferation;
- whether hidden automation or visible controls produce greater trust.

A particularly important controlled task is:

1. discover attribute A;
2. discover attribute B in another branch;
3. compose A+B;
4. reset the image seed;
5. recover both attributes without restoring either source image.

The baseline cannot solve this cleanly without luck or a prompt. The concept-lane designs are intended to make it a first-class operation.

## 12. Current implementation boundary

The three executable UIs share one backend, session API, renderer, learner, planner, history, and persistent atlas. The experimental concept library is currently stored in browser local storage and scoped by `control_basis_revision`. It therefore transfers between the three UI experiments in the same browser but not yet between devices.

The backend accepts three explicit New-world policies:

```text
taste_guided
neutral
composition(target_action)
```

This is enough to test whether a non-image composition can be learned, edited, and recast. It is not yet enough to claim that concept lanes improve the server planner. Promotion to core state should follow evidence from the UI experiments.

## 13. Design recommendation

Retain current-image anchoring for immediate comparison, but stop treating it as the only representation of intent.

The recommended product trajectory is:

1. test **implicit lanes** first;
2. make **Recast learned mix** the only new primary action;
3. keep tri-state lane controls behind progressive disclosure;
4. use the concept shelf and lane board as research interfaces;
5. after validation, persist concept state server-side and allow the planner's proposal center to blend current realization and active composition;
6. keep the current image as the truthful outside option even when proposals originate elsewhere.

The resulting mental model is:

\[
\boxed{\text{one image to compare against}\;\neq\;\text{one image to remember everything through}}
\]

## References

- Evan Shimizu, *Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces*, UIST 2020; and CMU-CS-20-104 doctoral thesis.
- Ryan Murdock, [*Generative Recommenders*](https://rynmurdock.github.io/writing/generative_recommenders.html), 2024, with the [`generative_recommender`](https://github.com/rynmurdock/generative_recommender) and [`preference-prior`](https://github.com/rynmurdock/preference-prior) prototypes.
- [Evan Shimizu review](02_EVAN_SHIMIZU_DESIGN_ADJECTIVES.md).
- [Ryan Murdock review](01_RYAN_MURDOCK_GENERATIVE_RECOMMENDERS.md).
- [Control-spaces review](04_GENERATIVE_CONTROL_SPACES_AND_DIRECTIONS.md).
- [Core mechanics review](07_CORE_MECHANICS_AND_USER_ACTIONS_DESIGN_REVIEW.md).
