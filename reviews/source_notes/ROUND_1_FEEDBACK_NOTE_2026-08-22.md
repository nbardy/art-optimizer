# Art Optimizer — Round 1 Feedback Note

Date: 2026-08-22
Test configuration: FLUX.2 Klein 4B, BF16, 1024×1024, four sequential candidates, shared-state UI experiments

## Overall assessment

The GPU/model path is fast and stable, but the current product behavior does not yet create the feeling of meaningfully evolving an image or learning reusable visual concepts. Several implementation choices are scientifically controlled, but the UI presents them as broader creative capabilities than they currently provide.

The most important mismatch is between what the controls imply and what the system actually does:

- “Reroll” sounds like a neutral request for more images, but it can train a negative preference.
- Clicking a candidate feels like it should modify the current image, but it actually promotes an already-rendered replacement and then samples around its numeric action.
- “Concepts” sound like shared visual patterns, but a single selected candidate generally becomes a new lane.
- The four UI experiments look different, but they operate on the same backend state, interaction semantics, learner, planner, candidate set, and concept library. They currently feel like skins or layouts rather than materially different experiments.

## 1. Reroll semantics are ambiguous and potentially misleading

Reroll currently means that the committed anchor wins against the meaningfully exposed candidates. If at least two ready candidates were visible long enough, the server records one weak multinomial preference observation with weight 0.35. A direct candidate selection has weight 1.0.

This is not four independent hard downvotes, but it is still negative evidence against every exposed candidate relative to the anchor. The browser-side concept library can also add opposition to concepts aligned with those rejected candidates.

If fewer than two candidates were meaningfully exposed, the round is skipped and no preference observation is recorded, although the search radius still widens.

Feedback:

- Users will naturally interpret “Reroll” as “show me more,” not “I prefer the current image to all of these.”
- Exploration intent and negative preference intent should not share one command.
- A user seeking novelty can accidentally train the system away from directions they did not actually dislike.

Recommended change:

Split this into two explicit actions:

1. “More variety” or “Shuffle” — no negative preference update; generate a new candidate round, preferably with fresh noise.
2. “None of these” — record the weak anchor-wins observation against meaningfully exposed candidates.

## 2. Visual variation is too low

The planner is producing numerically different 8D actions, including some candidates far from the anchor. The low visible variation primarily comes from the renderer mapping:

- Every candidate and reroll within a world uses the same world seed.
- Candidates differ only through relatively modest prompt-embedding perturbations.
- FLUX uses embedding strength 0.24, divided by √8 across the semantic directions.
- Generation uses four inference steps and guidance 1.0.
- A coherence instruction encourages preservation.

The result is a controlled same-noise comparison, but it often looks like four near-duplicates. Reroll changes action proposals and widens the trust region, but it does not change the diffusion seed. “New world” is currently the operation that produces a genuinely different stochastic composition.

Recommended change:

Use a hybrid candidate slate:

- Candidate 1: same seed, small local refinement.
- Candidate 2: same seed, stronger semantic-axis change.
- Candidate 3: fresh deterministic seed, nearby preferred attributes.
- Candidate 4: fresh deterministic seed, broad exploration or alternate taste mode.

Also make embedding strength configurable and benchmark approximately 0.24, 0.40, and 0.55. Add perceptual-diversity measurement because distance in the numeric action space does not guarantee visible difference.

## 3. Clicking a candidate does not edit the current image

A candidate is already a complete rendered PNG with an assigned 8D action. Clicking it:

1. promotes that exact candidate image to the committed image;
2. promotes its existing 8D action to become the new anchor;
3. records it as preferred over the anchor and exposed siblings;
4. generates another candidate round around the selected action.

The current image’s pixels or latent representation are not supplied to FLUX. The next images are fresh text-to-image generations using the world prompt, world seed, and different prompt embeddings.

Feedback:

This behaves like selecting successive points in a pre-rendered search process, not applying an attribute change to the current image and producing a true descendant. The UI language and visual presentation imply image evolution more strongly than the renderer supports.

Potential directions:

- Keep the current selection model but describe it honestly as searching a controlled generative space.
- Or introduce an image-conditioned/editing renderer, latent reuse, inversion, or another parent-conditioned mechanism so descendants genuinely inherit from the committed image.
- Store seed/noise provenance per design rather than only at the world level if individual images can have distinct stochastic roots.

## 4. The 8D control space is hand-authored, not discovered

The eight controls are manually defined prompt contrasts:

1. close-up ↔ expansive composition;
2. organic ↔ geometric form;
3. cool/restrained ↔ warm/saturated palette;
4. soft/diffuse ↔ dramatic/directional lighting;
5. minimal ↔ intricate detail;
6. matte/painterly ↔ glossy/translucent material;
7. still/orderly ↔ dynamic/turbulent motion;
8. abstract/stylized ↔ materially realistic rendering.

For each world prompt, the system encodes the base prompt plus positive and negative endpoint prompts for all eight axes. Each direction is half the positive-minus-negative embedding difference, RMS-normalized. A candidate action in [-1, 1]^8 is converted into a mixed prompt embedding and passed to FLUX.

The planner constructs a pool of 1,024 actions:

- 512 local Gaussian proposals around the current action;
- 256 global Sobol proposals;
- 256 proposals directed toward persistent taste or the neutral origin.

It selects four roles: best local continuation, diverse posterior sample, uncertainty probe, and controlled surprise.

Feedback:

- These directions are assumptions, not validated independent visual attributes.
- Axes may be entangled or weak for a particular prompt.
- Large numeric action distance can still produce little perceptual difference.
- The system currently optimizes in action space without closing the loop on actual perceptual output diversity.

Recommended changes:

- Run fixed-seed coordinate sweeps for every axis and several prompts.
- Measure perceptual effect size, monotonicity, duplication, and axis entanglement.
- Whiten or orthogonalize directions where useful.
- Remove or replace axes that do not produce reliable visual changes.
- Incorporate image-embedding diversity into candidate selection or reranking.
- Expose dominant candidate-axis deltas in a diagnostic mode so behavior is auditable.

## 5. Concept Shelf is not extracting shared visual concepts

The current implementation does not learn concepts from image content. When a candidate is committed, it computes:

    delta = chosen 8D action − anchor 8D action
    direction = normalize(delta)

It merges this observation into an existing lane only if action-direction cosine similarity is at least 0.82. Otherwise it immediately creates a new “Lane N.” A single committed image is enough to create an active lane.

Consequences:

- Most selected images become separate attributes.
- Visually similar changes may fail to merge because their numeric action deltas differ.
- No image embeddings, captions, or shared visual features are analyzed.
- Singleton lanes immediately participate in Recast composition.
- The shelf looks like a record of individual selections rather than learned recurring preferences.

A candidate favorite alone does not create a lane; committing/selecting the candidate creates the concept evidence.

Recommended concept pipeline:

    committed comparison
    → action-delta evidence
    → visual-delta embedding
    → provisional cluster
    → repeated supporting choices
    → promoted reusable concept

Each observation should contain:

- chosen-action minus anchor-action;
- chosen-image embedding minus anchor-image embedding;
- prompt/world/control-basis identity;
- seed relationship;
- positive selection or reroll evidence.

Concepts should merge using action similarity, visual-delta similarity, and outcome consistency. One image should be an exemplar, not an entire attribute.

Near-term improvements:

- Lower or adapt the action merge threshold from 0.82 toward roughly 0.65–0.70.
- Require two or three supporting selections before activation.
- Keep singleton evidence provisional and exclude it from Recast.
- Periodically merge compatible provisional clusters.
- Show support counts and multiple exemplars.

Proper version:

- Compute meaningful image embeddings rather than relying on simple RGB statistics.
- Perform online clustering over combined visual and action evidence.
- Name concepts from aggregate axis loadings and image/caption differences.
- Store concept evidence server-side instead of only in browser localStorage.
- Allow manual merge, split, activation, and correction.

## 6. The UI experiments share the same underlying experiment

The UI routes change layout and disclosure:

- Current image
- Implicit lanes
- Concept shelf
- Lane board

However, they share the same session ID, backend state machine, committed design, candidate round, planner, learner, world, history, favorites, persistent atlas, and browser concept library. Switching routes therefore preserves state and usually presents the same candidates and concepts.

State continuity is useful for comparing presentation without restarting the creative session, but it means these are currently UI variants, not materially different product or algorithm experiments.

Feedback:

The variants do not yet test genuinely different hypotheses. They mostly rearrange the same controls and information. If the goal was to compare distinct interaction models, the experiment boundary is too shallow.

Recommended change:

Define each experiment by an explicit policy bundle, not only an HTML/JS layout. Examples:

- Current Image: no visible concepts; simple select, favorite, neutral shuffle.
- Implicit Lanes: concepts learned silently; only stable concepts affect generation.
- Concept Shelf: explicit concept activation, strength, merge, split, and recast.
- Lane Board: candidates generated per lane with controlled axis interventions.

Each experiment should declare independently:

- candidate-generation policy;
- seed/noise policy;
- exposure semantics;
- preference-update policy;
- concept promotion threshold;
- concept visibility/editability;
- reroll meaning;
- recast behavior;
- metrics and success criteria.

The experiments may share immutable event facts, images, and model infrastructure, but should maintain separate experiment projections or policy state when their semantics differ. Switching UI should not silently imply that all variants are operating the same hypothesis.

## Recommended Round 2 priorities

1. Split “More variety” from “None of these.”
2. Introduce a hybrid shared-seed/fresh-seed candidate slate.
3. Make embedding strength configurable and run controlled sweeps.
4. Prevent singleton choices from immediately becoming active concepts.
5. Add visual-delta embeddings and provisional concept clustering.
6. Turn UI variants into explicit policy experiments rather than layouts over one controller.
7. Decide whether Art Optimizer is primarily generative-space search or true parent-conditioned image evolution, then align the renderer and language accordingly.

## Core product question

The next round should decide which product is being built:

A. A scientifically controlled preference optimizer over a fixed generative world, where same-seed comparisons and absolute coordinates are primary; or

B. An intuitive creative evolution tool, where selecting an image visibly transforms that image, reroll means novelty without punishment, and reusable concepts emerge from repeated visual patterns.

The current system is architecturally closer to A but is presented experientially closer to B. Most of the Round 1 friction comes from that mismatch.
