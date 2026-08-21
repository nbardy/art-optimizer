# Art Optimizer Research Synthesis

## 1. Purpose

The five research reviews establish that Art Optimizer sits at the intersection of several mature-but-incomplete lines of work:

```text
Murdock / generative recommenders
    persistent generative preference representations

Shimizu / Design Adjectives
    fast local subjective-function learning and gallery exploration

preference learning / PBO
    discrete-choice likelihoods, uncertainty, and next-query selection

generative control research
    directions, references, attention, adapters, and noise geometry

interactive generative search
    low-friction judgments, fatigue, agency, branching, and recovery
```

No reviewed system supplies the complete stack. The research opportunity is the integration—and the empirical questions created by that integration.

## 2. The central decomposition

Art Optimizer should be modeled as four timescales and representations.

### 2.1 Persistent preference atlas

The long-lived user model is a multimodal set:

\[
\mathcal P_u
=\{P_k\}_{k=1}^{K},
\]

where each component stores a visual preference region, uncertainty, proposal mass, evidence mass, recency, compatible action heads, and replayable exemplars.

Its job is:

- cross-session continuity;
- cold-start guidance for a new world;
- retrieval of relevant favorites;
- preservation of dormant interests;
- broad mode selection and crossover;
- eventual collaborative or sequence-prior conditioning.

This is the line most directly informed by [Murdock's generative-recommender work](https://rynmurdock.github.io/writing/generative_recommenders.html), extended from one user representation to a set of coherent modes.

### 2.2 World context

A world fixes the conditions under which actions are comparable:

\[
W=(\theta,s,c,B),
\]

where:

- \(\theta\): model/checkpoint;
- \(s\): stochastic root;
- \(c\): prompt, references, aspect ratio, preservation conditions;
- \(B\): versioned control basis/codec.

Within a world, candidate actions should not secretly alter these conditions.

Its job is:

- causal attribution among candidates;
- replay;
- local geometry;
- safe persistent-atlas compatibility;
- clear New-world semantics.

### 2.3 Branch-local posterior

A branch learns the user's current intent quickly:

\[
q_t(w)
=p(w\mid\mathcal D_{\text{branch},t}).
\]

Its job is:

- immediate interpretation of commit/reroll choices;
- uncertainty estimation;
- local improvement;
- adaptation to changing intent;
- restoration with history.

This line is most directly informed by [Design Adjectives](https://doi.org/10.1145/3379337.3415866), preference learning, and preferential Bayesian optimization.

### 2.4 Generator action manifold

The renderer maps an absolute bounded action into an image:

\[
I=G_\theta(W,a),
\qquad a\in\mathcal A_W.
\]

Its job is:

- produce judgeable alternatives;
- preserve fixed world conditions;
- support different quantities of learned controls;
- expose enough smooth, nonredundant variation for optimization;
- declare scope and replay guarantees.

This line is informed by GAN directions, StyleCLIP, FABRIC, GimmBO, MultiBO, and diffusion/flow model internals.

## 3. A unified probabilistic view

Let \(\phi(I)\) be a model-neutral visual feature vector. The persistent atlas defines a context-sensitive utility prior:

\[
m_u(I\mid c,h)
=\log\sum_{k=1}^{K}
\pi_k(c,h)
\exp\bigl(u_k^\top\phi(I)\bigr).
\]

The branch-specific utility can be decomposed as:

\[
f_b(a)
=\lambda_t m_u(G(W,a)\mid c,h)
+\delta_b(a).
\]

Interpretation:

- \(m_u\): what this person broadly and historically tends to value;
- \(\delta_b\): what this branch is teaching us right now;
- \(\lambda_t\): how strongly persistent memory should initialize the current branch.

At a new world, local data is scarce and \(\lambda_t\) can be larger. As branch choices accumulate, the local residual should dominate.

The displayed alternatives include anchor \(a_{t0}\) and meaningfully exposed candidates \(a_{t1:m}\). The observation is:

\[
P(y_t=j)
=\frac{\exp(f_b(a_{tj})/\tau)}
{\sum_{k=0}^{m}\exp(f_b(a_{tk})/\tau)}.
\]

This one likelihood supports both:

- candidate selection, \(j>0\);
- valid reroll/anchor selection, \(j=0\).

## 4. Candidate selection as a four-purpose slate

The planner should not ask only:

> Which action has the highest expected utility?

It must ask:

> Which set of four images gives the user useful progress, meaningful alternatives, information, and discovery without becoming incoherent?

A conceptual slate objective is:

\[
J(S)=
\sum_{a\in S}\mu(a)
+\beta\sum_{a\in S}\sigma(a)
+\lambda_D D(S)
+\lambda_P P_{\text{persistent}}(S)
-\lambda_J J_{\text{catastrophic}}(S).
\]

The four internal roles approximate this objective:

| Slot purpose | Research ancestry | Product purpose |
|---|---|---|
| Best local | Design Adjectives Towards; exploitation | likely branch progress |
| Diverse posterior | Thompson/PBO; iso-preference exploration | another plausible interpretation |
| Informative probe | active preference learning | reduce important uncertainty |
| Controlled surprise | Away/outside-prior/novelty | challenge basin without random reset |

The roles are policy metadata, not labels shown to the user.

## 5. Interaction semantics are part of the model

The action vocabulary determines the data-generating process. It is not a thin UI wrapper around a reward model.

### Preview

No model update. It improves human judgment quality by letting a thumbnail be seen in full context.

### Commit

One branch-local slate-choice observation plus weak persistent evidence.

### Reroll

Anchor wins against meaningfully exposed candidates with low observation weight. No ordinary persistent update.

### Favorite

Strong persistent evidence, independent of branch navigation.

### New world

New stochastic root and local reset, with no negative label for the previous world.

### Restore

Exact world/design/posterior/search recovery; moderate persistent evidence that the checkpoint retained value.

### Export

Recommended next addition: strongest durable positive evidence because the design crossed from exploration into actual use.

This event-specific interpretation is one of the most important Art Optimizer extensions. A generic “like/dislike” stream would discard distinctions needed by both local search and persistent memory.

## 6. What comes from whom

### Ryan Murdock

Directly motivates:

- interaction-conditioned generation;
- visually actionable user representations;
- iterative generated-feedback loops;
- sequence-conditioned preference priors;
- the artist-as-curator framing.

Art Optimizer extends:

- one user representation to a multimodal atlas;
- qualitative feedback to explicit event semantics;
- representation learning to active next-query selection;
- session iteration to replayable worlds and branches.

### Evan Shimizu and Design Adjectives

Directly motivates:

- a learned subjective function over design controls;
- one current design with generated alternatives;
- full-context hover preview;
- model-guided galleries;
- Towards, Away, Similar Score, and Axis exploration modes;
- coarse-to-fine exploration and refinement.

Art Optimizer modifies:

- scalar ratings into multi-choice observations;
- mean-driven rejection sampling into uncertainty-aware slate planning;
- explicit design parameters into a versioned image-model codec;
- one adjective/session into persistent plus local preference structure.

### Preference-learning literature

Directly contributes:

- latent utility models;
- pairwise and multinomial likelihoods;
- uncertainty-aware acquisition;
- preferential Bayesian optimization;
- active use of scarce human judgments;
- treatment of inconsistency and nonstationarity.

Art Optimizer adds:

- current anchor as an explicit outside option;
- meaningful exposure masking;
- four-role slate policy;
- event-specific persistence;
- branch restoration and replay.

### Generative-control literature

Directly contributes:

- latent and activation directions;
- text-guided generator manipulation;
- reference/attention feedback conditioning;
- adapter-weight design spaces;
- compact attention intervention spaces;
- amount-controlled edits.

Art Optimizer adds:

- one model-codec protocol;
- direction scope and provenance;
- fixed-world comparison semantics;
- cross-model basis isolation;
- a preference optimizer over hybrid controls.

### Interactive-search literature

Directly contributes:

- human recognition as an optimization signal;
- fatigue as a first-class bottleneck;
- gallery-based judgments;
- the need to design answerable queries;
- lightweight swipe/choice loops;
- evidence that preference can shift through inspiration.

Art Optimizer adds:

- commit versus favorite;
- reroll versus New world;
- exact branch forest;
- persistent multi-interest memory;
- avoidance of engagement-based implicit rewards.

## 7. The current implementation's scientific status

### Implemented

- one current image with four candidate slots;
- preview/commit separation;
- anchor-outside-option reroll;
- explicit exposure masking;
- Bayesian quadratic local learner;
- role-balanced finite-pool planner;
- multimodal persistent atlas;
- exact world/design/branch persistence;
- procedural reference renderer;
- local FLUX and Krea model codecs;
- prompt-embedding direction mode;
- prompt-string comparison mode;
- SSE progressive image delivery;
- branch history and restoration.

### Structurally implemented but not empirically validated

- the eight semantic embedding directions for FLUX and Krea;
- the selected direction strengths;
- cross-prompt smoothness;
- preference progress under real models;
- model-specific latency and VRAM;
- whether role-balanced quartets outperform simpler planners;
- persistent-atlas benefit across sessions.

### Not implemented as a validated product feature

- reference-image atlas conditioning;
- attention-space search;
- adapter-mixture search;
- learned direction discovery;
- calibrated direction sliders;
- export/provenance interaction;
- collaborative preference priors;
- sequence-conditioned atlas model;
- production authentication and multi-user isolation.

## 8. Core research hypotheses

### H1: Multi-choice browsing can outperform prompt refinement

For users whose target is tacit or evolving, repeated visual choice will reach a satisfying artifact in fewer cognitive steps than prompt-only refinement.

### H2: Separating local and persistent preference improves both

A fast local posterior will follow the current branch without erasing stable long-term taste, while a persistent atlas will reduce cold-start rounds across worlds and sessions.

### H3: Four role-diverse candidates outperform four top-scoring candidates

A role-balanced slate will reduce repetition, improve model calibration, and increase discovery without substantially increasing reroll rate.

### H4: Fixed stochastic roots improve preference attribution

Holding root noise fixed within a world will make local actions smoother and help the learner infer semantic preference rather than lucky composition.

### H5: Exact branch recovery increases exploration

Users will take more creative risks when every committed state remains recoverable and forkable.

### H6: Favorite is not equivalent to commit

Favorite events will better predict later revisit/export than ordinary branch commits and should receive substantially stronger persistent weight.

### H7: Prompt-embedding directions need model-specific validation

Readable endpoint phrases will not guarantee monotonic, independent, or cross-model-consistent controls. Model-specific sweeps and action heads will outperform naive shared coordinates.

## 9. The strongest defensible contribution statement

A conservative project description is:

> Art Optimizer is an open research platform for human-in-the-loop image evolution. It combines persistent multimodal preference memory, fast branch-local discrete-choice learning, uncertainty- and diversity-aware four-candidate planning, versioned generator control codecs, and replayable branching in a single interaction model.

This statement describes an implemented integration. It does not claim superiority, convergence, or a novel optimizer until comparative evidence exists.

## 10. Claims the project should avoid

Do not claim:

- “the first generative recommender”;
- “RL learns your taste” when the current loop is a preferential bandit;
- “semantic latent directions” before control-basis validation;
- “the model knows what you like” from a few clicks;
- “personalization” without reporting what is persistent and what is local;
- “four choices are optimal”;
- “reroll is a downvote” without qualification;
- “Krea and FLUX use the same latent space”;
- “fixed seed guarantees only one semantic attribute changes”;
- “persistent priors improve outcomes” before an ablation;
- “user preference is stationary”;
- “engagement proves creative value.”

## 11. Architecture implications

The research decomposition supports narrow module boundaries:

```text
Event model
    exact user and system facts

PreferenceModel
    branch-local posterior

PreferenceAtlas
    slow multimodal memory

CandidatePlanner
    acquisition and slate diversity

ModelCodec
    canonical action -> model intervention

ImageRenderer
    deterministic/best-effort execution

Client
    preview, commands, exposure, history
```

Experiments should swap one layer at a time while retaining the same events and replay receipts.

## 12. Research sequence

### Stage 1: validate interaction and event semantics

- accidental commits;
- preview comprehension;
- reroll interpretation;
- favorite/commit distinction;
- history recovery;
- two/four/six candidates.

### Stage 2: validate model control bases

- prompt versus embedding controls;
- fixed-root sweeps;
- smoothness and preservation;
- FLUX versus Krea;
- correlated noise variants;
- reference exemplars.

### Stage 3: validate local learner and planner

- random/local baseline;
- top-four exploitation;
- Thompson slate;
- current role-balanced policy;
- GP/PBO alternative;
- nonstationary learner.

### Stage 4: validate persistent memory

- no memory;
- weighted mean;
- current online atlas;
- exemplar retrieval;
- sequence prior;
- collaborative/content hybrid.

### Stage 5: consolidate and refine

- learned directions;
- axis sweeps;
- user adapters;
- offline DPO/DRaFT;
- production multi-user evaluation.

## 13. Final synthesis

The research case for Art Optimizer is strong because the underlying parts have credible precedents. The implementation risk is equally real because each precedent assumes a different control space, signal, horizon, or target.

The project should proceed with this attitude:

```text
prior work justifies building the loop
only experiments justify claiming the loop works better
```

The immediate scientific objective is not to prove a grand theory of aesthetic preference. It is to determine whether a lean, replayable four-choice interface can turn generator controls and persistent memory into a genuinely better creative instrument.
