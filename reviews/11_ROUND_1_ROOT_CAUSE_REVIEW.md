# Round 1 Root-Cause Review

**Status:** post-test design and systems review  
**Date:** 2026-08-22  
**Tracking issue:** [#10 — Round 2: separate novelty, preference, perceptual diversity, concepts, and true image evolution](https://github.com/nbardy/art-optimizer/issues/10)  
**Primary observation source:** [Round 1 feedback note](source_notes/ROUND_1_FEEDBACK_NOTE_2026-08-22.md)

## Executive judgment

The first real FLUX.2 Klein session did not reveal one isolated tuning bug. It revealed a contract mismatch between four layers:

```text
what the UI says
    image evolution and reusable concepts

what the event model means
    discrete choices over an anchor and four alternatives

what the planner optimizes
    utility and Euclidean diversity in an eight-dimensional authored action space

what the renderer does
    fresh text-to-image generation with one world seed and perturbed prompt embeddings
```

The GPU path is not the problem. The model is fast enough. The interaction loop is technically stable. The failure is that controlled generative-space search is being presented as if it were parent-conditioned image evolution and visual-concept discovery.

That distinction matters because each product demands a different renderer, data model, action vocabulary, and evaluation protocol.

## Evidence base

This review is grounded in:

1. the [Round 1 feedback note](source_notes/ROUND_1_FEEDBACK_NOTE_2026-08-22.md), produced after testing FLUX.2 Klein 4B in BF16 at 1024×1024 with four sequential candidates;
2. the current `main` implementation;
3. the existing source reviews of [Evan Shimizu's Design Adjectives](02_EVAN_SHIMIZU_DESIGN_ADJECTIVES.md) and [Ryan Murdock's Generative Recommenders](01_RYAN_MURDOCK_GENERATIVE_RECOMMENDERS.md);
4. the official [Design Adjectives project page](https://graphics.cs.cmu.edu/projects/design-adjectives/) and UIST paper ([DOI](https://doi.org/10.1145/3379337.3415866));
5. Murdock's [Generative Recommenders essay](https://rynmurdock.github.io/writing/generative_recommenders.html), [`generative_recommender`](https://github.com/rynmurdock/generative_recommender), and [`preference-prior`](https://github.com/rynmurdock/preference-prior) prototypes.

Source status matters. Design Adjectives is peer-reviewed work supported by a thesis, source code, user studies, and professional case studies. Murdock's work is a highly relevant author essay and released research prototypes, not a controlled production evaluation.

## What the implementation actually is

The current system is best described as:

> An interactive preference optimizer over a bounded, hand-authored prompt-embedding control space, with a current rendered image as the outside option and a browser-local heuristic library of accepted action deltas.

That is a legitimate research system. It is simply narrower than the product language implied.

### Immediate branch-local model

The current image is the comparison anchor. A selection records one multinomial observation over the anchor plus meaningfully exposed alternatives. A valid reroll records the anchor as winner with lower weight.

Relevant code:

- [`ArtOptimizerService.commit_candidate`](../art_optimizer/service.py)
- [`ArtOptimizerService.reroll`](../art_optimizer/service.py)
- [`BayesianChoiceModel`](../art_optimizer/preference.py)

### Candidate planner

The planner searches 1,024 points in an eight-dimensional absolute action space:

- half local Gaussian proposals;
- one quarter global Sobol proposals;
- one quarter proposals directed toward atlas guidance or the neutral origin.

It chooses four roles by utility, uncertainty, action-space distance, and atlas proximity.

Relevant code:

- [`CandidatePlanner`](../art_optimizer/planner.py)
- [`PlannerContext`](../art_optimizer/planner.py)

### Renderer/control map

Every real-model action is compiled through eight manually authored semantic contrasts:

```text
composition
form
palette
lighting
detail
material
motion
realism
```

FLUX.2 Klein currently uses embedding strength `0.24`, four inference steps, guidance `1.0`, and a coherence-oriented finish instruction.

Relevant code:

- [`SemanticDirectionCodec`](../art_optimizer/model_codec.py)
- [`_AXES`](../art_optimizer/model_codec.py)
- [`LocalDiffusersRenderer`](../art_optimizer/diffusers_renderer.py)
- [`build_direction_bank`](../art_optimizer/embedding_conditioning.py)

### Browser concept model

The concept experiment observes only the selected action delta relative to the current action. It immediately creates a lane unless cosine similarity with an existing lane is at least `0.82`. Support begins at `1`, while automatic activation requires only support minus opposition of `0.25`.

Relevant code:

- [`ConceptLibrary.observeCommit`](../art_optimizer/static/experiment_core.js)
- [`ConceptLibrary.observeReroll`](../art_optimizer/static/experiment_core.js)
- [`ConceptLibrary.composition`](../art_optimizer/static/experiment_core.js)

### UI experiment boundary

The four UI routes declare presentation metadata but share one backend policy and one browser concept library.

Relevant code:

- [`UIExperiment`](../art_optimizer/ui_experiments.py)
- [`createStudioController`](../art_optimizer/static/experiment_core.js)

## Root-cause tree

## Root cause 0: product-language mismatch

The top-level problem is not “variation too low.” It is that the system's visible nouns and verbs imply stronger semantics than the underlying objects provide.

| Visible term | User expectation | Current implementation |
|---|---|---|
| Current image | parent object being edited | outside-option rendering at one absolute action |
| Candidate | possible edit/descendant | complete text-to-image rendering at another action |
| Reroll | neutral request for more options | weak anchor-wins preference update when sufficiently exposed |
| Concept | recurring visual attribute | normalized accepted action delta, often supported once |
| Recast | preserve concepts in a new realization | sum browser-local action directions and start a new world |
| UI experiment | materially different interaction hypothesis | different projection/disclosure over one shared controller |

This mismatch causes the remaining failures to feel worse because the user interprets them against the wrong contract.

## Root cause 1: exploration and preference are overloaded

`Reroll` performs two jobs:

1. request another slate;
2. state that the current anchor is preferred to exposed alternatives.

The server's statistical behavior is defensible only for job 2. The label is naturally interpreted as job 1.

The browser concept library then adds a second negative side effect by increasing opposition for concepts aligned with exposed candidates.

### Why this is structural

No weight adjustment fixes the semantic ambiguity. Reducing `0.35` to `0.10` still means “negative evidence.” Increasing the exposure threshold reduces accidental updates but does not make the command truthful.

### Required correction

Introduce separate event types:

```text
ShuffleRequested
    no preference update
    explicit novelty/seed policy

NoneOfTheseSelected
    anchor-wins observation
    only against qualified alternatives

CandidateMarkedBroken
    zero preference effect
```

These must remain distinct raw facts in storage, even if a future model infers relationships among them.

## Root cause 2: numerical diversity is not perceptual diversity

The planner rewards Euclidean action distance:

\[
\|a_i-a_j\|_2.
\]

The user sees rendered-image distance:

\[
D_\phi\left(\phi(G(a_i,z)),\phi(G(a_j,z))\right).
\]

There is no reason for those distances to agree. The eight directions may be weak, redundant, prompt-dependent, or entangled. The fixed seed further encourages composition-level similarity.

### Why the “global Sobol pool” did not save the slate

A broad proposal pool matters only if the renderer map has broad, reliable output effects. Sobol coverage over a weak or collapsed chart remains perceptually narrow.

### Required correction

Close the loop on rendered outputs:

```text
propose actions
    → render cheap/low-resolution pool or estimate local action-to-image map
    → compute perceptual features
    → select a utility/uncertainty/diversity slate in image space
```

The product should never again use action distance alone as evidence that a “surprise” candidate is visually surprising.

## Root cause 3: the stochastic variable is hidden inside “New world”

Within a world, candidates reuse the world seed. This creates controlled comparisons but starves the ordinary loop of composition-level novelty. The only command that reliably changes stochastic composition is New world.

This is too coarse. It makes the user choose between:

- tiny same-seed variations;
- abandoning the world entirely.

### Required correction

Make seed/noise relationship candidate metadata:

```text
same_root
correlated_root(rho)
fresh_root
parent_inversion
```

A slate may intentionally combine these. The user does not necessarily need to see technical seed language, but the generation policy and event log must know it.

## Root cause 4: the current image is not a generative parent

Selecting a candidate promotes an already-rendered `DesignState`. The next round is generated from the world prompt, seed, and selected action. The renderer does not consume the selected image pixels, an inversion state, or a parent latent.

This means the branch graph records preference-navigation ancestry, not generative inheritance.

### Why this matters

A user can perceive a candidate as containing a valuable local detail that disappears in the next round even when the action remains nearby. That is not necessarily a bug in text-to-image generation; it is a mismatch between navigation ancestry and visual ancestry.

### Two valid product responses

**Treatment A — honest generative-space search**

- retain the current renderer;
- call the interaction “search,” “navigate,” or “continue from this region”;
- show seed/control provenance;
- optimize candidate-space quality.

**Treatment B — true image evolution**

- add an image-conditioned/editing, latent-reuse, or inversion renderer;
- persist parent-conditioning state per design;
- define preservation objectives and edit strength;
- test whether descendants visibly inherit the selected image.

These should be separate policy experiments, not one UI toggle over the same renderer.

## Root cause 5: authored axes are treated as validated attributes

The axis names are plausible product hypotheses. They are not yet demonstrated model controls.

A valid control basis should have measured:

- effect size;
- monotonicity;
- smoothness;
- redundancy;
- off-target drift;
- cross-seed transfer;
- cross-prompt transfer;
- validity radius.

Until then, the eight axes are codec implementation details, not learned concepts.

### Evan Shimizu comparison

Design Adjectives operates over a declared parameterized design space and learns a subjective function over that space. It also provides multiple exploration operations, including Towards, Away, Similar Score, and Axis. The stronger lesson is that the parameterization and the learned function must be inspectable and useful to the designer.

Our current system copied the broad gallery-plus-model pattern but skipped two crucial disciplines:

1. validate that the coordinates provide useful design control;
2. expose distinct exploration semantics instead of compressing them into select/reroll/New world.

## Root cause 6: concepts are evidence-free labels on singleton movements

A single selected action delta can become an active lane. The algorithm does not compare image content, visual deltas, captions, seed relationship, or repeated outcomes.

### What a concept observation should be

At minimum:

\[
o_t = \left(
\Delta a_t,
\Delta \phi_t,
\text{context}_t,
\text{seed relation}_t,
\text{outcome}_t
\right),
\]

where:

\[
\Delta a_t=a_{\text{chosen}}-a_{\text{anchor}}
\]

and:

\[
\Delta \phi_t=\phi(I_{\text{chosen}})-\phi(I_{\text{anchor}}).
\]

One observation should normally create a provisional hypothesis, not a durable concept.

### Ryan Murdock comparison

Murdock's generative recommender work connects interaction histories to visual representations usable for generation. The follow-up Preference Prior explicitly explores predicting a held-out preferred-media embedding from a sequence of preferred-media representations.

The stronger lesson is recurrence across media history. A generative preference representation should summarize structure across multiple interactions. Our current action-delta shelf does not yet do this. It is closer to a lightweight movement log.

## Root cause 7: UI experiments do not own policy

The current experiment registry describes layouts and concept visibility. It does not declare:

- seed/noise policy;
- candidate-generation policy;
- preference-observation policy;
- concept promotion rules;
- candidate count;
- renderer mode;
- recast meaning;
- success metrics.

As a result, switching UI changes presentation while preserving the exact hypothesis being tested.

### Required correction

A UI experiment should resolve to a typed policy bundle:

```text
ExperimentPolicy
    renderer mode
    candidate policy
    noise policy
    command semantics
    preference learner
    concept learner
    concept visibility/editability
    projection schema
    metrics
```

Immutable events and generated artifacts may be shared. Derived projections and learner state must be isolated when semantics differ.

## What is worth preserving

The test did not invalidate everything.

Keep:

- exact branch/history recovery;
- explicit exposure qualification;
- immutable designs and replay metadata;
- separate visible version and mutation version;
- modular model codecs;
- current image as a valid outside option for explicit comparison;
- streamed candidates;
- the ability to retain the current baseline as a controlled-search treatment.

The mistake would be deleting a scientifically coherent baseline instead of relabeling it and comparing it with more creative treatments.

## What should not be claimed after Round 1

Do not claim that the current system:

- learns reusable visual concepts;
- performs parent-conditioned image evolution;
- produces perceptually diverse four-candidate slates;
- validates the eight semantic directions;
- tests four materially different product hypotheses;
- has demonstrated that recast preserves learned taste across seeds.

Safe wording:

> Round 1 implemented and tested a stable preference-search baseline over a hand-authored prompt-embedding action space. The test exposed semantic, perceptual, and concept-learning limitations that define the Round 2 research program.

## Round 2 decision sequence

Do not begin by adding more controls.

1. Split neutral novelty from negative preference.
2. Add typed seed/noise relationships and a hybrid candidate slate.
3. Measure image-space diversity and axis effect before changing the preference learner.
4. Make concept evidence server-side and provisional.
5. Define at least one true parent-conditioned renderer treatment.
6. Convert UI experiments into policy bundles.
7. Compare treatments using the same prompts, budgets, and logged observation facts.

## Review conclusion

The core problem is not that the optimizer “needs more randomness.” It is that several different mathematical objects were collapsed:

```text
comparison anchor
proposal center
rendering parent
stochastic root
preference posterior
visual concept
persistent taste mode
UI experiment
```

Round 2 should separate those objects in both the data model and the user-facing action language. Once they are separate, the project can test multiple creative systems honestly instead of asking one eight-dimensional chart to impersonate all of them.
