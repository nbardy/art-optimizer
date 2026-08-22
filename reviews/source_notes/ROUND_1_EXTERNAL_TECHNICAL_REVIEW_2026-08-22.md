# External Technical Review — Round 1

**Date received:** 2026-08-22  
**Status:** source note; preserved substantially verbatim  
**Interpretation:** see [`../11_ROUND_1_ROOT_CAUSE_REVIEW.md`](../11_ROUND_1_ROOT_CAUSE_REVIEW.md)

This note is an external agent's technical audit of the first FLUX session and current implementation. Numerical claims from simulations should not be treated as canonical until the corresponding reproduction script, seed, and receipt are checked into the repository. The source is preserved so later reviews can distinguish external observations from project conclusions.

---

The verdict: the engineering scaffold is good, and the Bayesian choice update is mostly sound. What failed is the representation
  underneath it—and then the UI described experimental proxies as if they were learned visual understanding.

  The most accurate description of the current product is:

  > Art Optimizer searches a hand-authored eight-number prompt-embedding plane at one fixed seed. Concept Shelf stores vectors
  > corresponding to chosen moves. It does not edit parent images, discover visual attributes from pixels, or merge shared visual
  > patterns.

  That simpler statement explains essentially all of your Round 1 feedback.

  ## What actually happens

  For a prompt (p) and action (a\in[-1,1]^8), the renderer constructs approximately:

  [
  e_p(a)=e_p(0)+\frac{0.24}{\sqrt 8}D_p a
  ]

  where the columns of (D_p) come from eight manually written prompt oppositions:

  - close-up ↔ wide
  - organic ↔ geometric
  - cool ↔ warm
  - diffuse ↔ dramatic lighting
  - minimal ↔ intricate
  - matte ↔ glossy
  - still ↔ turbulent
  - abstract ↔ realistic

  These axes are defined in art-optimizer/art_optimizer/model_codec.py:158, with their embedding directions constructed in art-
  optimizer/art_optimizer/embedding_conditioning.py:77.

  The image is then:

  [
  I_w(a)=G_\theta(z_w,e_p(a))
  ]

  Every candidate in a world gets the same prompt and seed. The parent image is never passed to FLUX; parent_design_id is lineage
  metadata only. You can see the complete renderer inputs in art-optimizer/art_optimizer/service.py:801.

  Therefore clicking a candidate does exactly this:

  promote the already-rendered candidate PNG/action
  → make it the current branch point
  → propose four more absolute coordinates

  It does not:

  extract the quality you liked
  → update an attribute
  → edit or regenerate the parent using that attribute

  So your observation was correct. The current click behavior is faithful to the original optimizer contract, but Concept Shelf creates
  a different expectation.

  ## Why the images look so similar

  The planner is not actually choosing four nearby numerical actions. In a 100-round simulation of the current cold-start planner,
  median distances from the anchor were:

   Candidate role         Median action distance
  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━
   best local                               0.62
  ─────────────────────  ────────────────────────
   diverse posterior                        2.12
  ─────────────────────  ────────────────────────
   informative probe                        2.55
  ─────────────────────  ────────────────────────
   controlled surprise                      2.51

  Those are large moves inside an eight-dimensional ([-1,1]) cube. The problem is that numerical distance is not perceptual distance.

  Let (D) contain the eight embedding directions. For two actions:

  # [
  |e(a)-e(b)|^2

  \frac{0.24^2}{8}(a-b)^TD^TD(a-b).
  ]

  The code normalizes each column’s RMS, but never measures the correlations in (D^TD). Two directions can be nearly identical, making
  a large action such as ((1,-1,0,\ldots)) almost cancel. The image generator then contributes another unknown Jacobian:

  [
  \text{perceptual distance}
  \approx
  \Delta a^TD^TJ_G^TWJ_GD\Delta a.
  ]

  The planner instead uses simply (|\Delta a|^2), in art-optimizer/art_optimizer/planner.py:67. Those metrics agree only if the
  combined renderer geometry is well-conditioned and approximately isotropic. Nothing tested that.

  The repository’s own design correctly called this a blocking experiment: axis sweeps, Jacobian conditioning, redundancy, perceptual
  calibration, and quartet duplicate tests were required before accepting the basis. See art-optimizer/docs/
  CONTROL_BASIS_EXPERIMENT.md:115 and art-optimizer/docs/IMPLEMENTATION_READINESS.md:120. Those experiments were never implemented or
  run.

  That is the central mistake: we ran the application smoke test before running the representation test.

  Fixed seed was not itself wrong. It was a scientifically good common-random-number control that isolates action effects. But it
  restricts exploration to one thin slice of FLUX’s distribution. Fresh-seed exploration should be an explicit “More variety”
  operation, not silently mixed into the action learner.

  ## The Bayesian part is mostly correct

  The local preference model has 44 parameters:

  [
  8\text{ linear}
  +8\text{ squared}
  +\binom82\text{ interactions}
  =44.
  ]

  For an exposed slate, the implementation maximizes a Gaussian-prior multinomial-logit posterior. Its negative Hessian is:

  [
  C_0^{-1}
  +
  \frac{\omega}{\tau^2}
  X^T(\operatorname{diag}p-pp^T)X,
  ]

  which is positive definite because (C_0^{-1}\succ0). Therefore the objective is strictly concave and has a unique MAP. The Newton
  update and Laplace covariance in art-optimizer/art_optimizer/preference.py:132 are correct for one sequential approximate-Bayesian
  update.

  But the model is far too expressive for the click budget. One five-way choice contributes Fisher information of rank at most four:

  [
  \operatorname{rank}(F)\le4.
  ]

  So at least eleven suitably diverse, fully exposed rounds are necessary before the data information can even span 44 dimensions.
  Early “personalization” is mostly prior geometry and hand-tuned planner coefficients.

  The implementation is also sequential assumed-density filtering rather than the spec’s batch Laplace re-fit. Consequently,
  observation order matters.

  ### What reroll means mathematically

  Backend reroll is one weak outside-option choice with weight (0.35):

  # [
  P(\text{anchor wins})

  \frac{1}{1+\sum_j e^{\Delta f_j/\tau}}.
  ]

  At zero weights its gradient is:

  [
  -\frac{0.35}{\tau(m+1)}\sum_jx_j.
  ]

  So reroll does not independently downvote all four images. It says jointly:

  > The anchor was preferred to this exposed slate.

  The preference function then generalizes that observation; it can theoretically lower some candidates more than others or even
  slightly raise one.

  Separately, Concept Shelf adds opposition only to existing lanes aligned at least 0.65 with an exposed rejected move. It does not
  downvote every lane.

  The product should split:

  - Keep current / none fit: weak preference observation.
  - More variety: no preference observation; explore another seed or basis region.

  ## Why every click becomes a “concept”

  Concept Shelf never examines pixels, captions, or image embeddings. On commit it computes only:

  [
  \delta=a_{\text{chosen}}-a_{\text{anchor}},
  \qquad
  d=\frac{\delta}{|\delta|}.
  ]

  It merges this with another lane only when cosine similarity is at least 0.82; otherwise it creates a new lane immediately. See art-
  optimizer/art_optimizer/static/experiment_core.js:142.

  For unrelated directions on the eight-dimensional unit sphere:

  [
  P(d_1^Td_2\ge0.82)\approx0.0034.
  ]

  That is about one match in 294 comparisons. Even with twelve unrelated existing lanes, the chance of matching any is only about 4%.

  Worse, a new lane starts with support 1, while automatic activation requires only:

  [
  1-0\ge0.25.
  ]

  So every first observation becomes an active concept. The JavaScript test explicitly requires this behavior.

  There is an impossibility proof here:

  > Two sessions with identical action deltas but completely different images produce identical concept libraries.

  Therefore the library cannot be extracting shared visual patterns. It is clustering selected motion vectors inside the eight pre-
  authored axes.

  It also confuses “everything that changed” with “the reason the user selected it.” If a candidate changed geometry, color, and
  lighting together but you selected it only for color, the shelf records all three as one reusable direction.

  ### Recast is even more revealing

  For a singleton lane, confidence is (1/(1+0+1)=0.5). Ignoring clipping, the recast contribution from one chosen move (x\rightarrow y)
  is:

  [
  a_C=0.5(y-x),
  ]

  not (y), and not (x+(y-x)).

  If (T) selections all become separate singleton lanes:

  # [
  a_C

  # \frac{1}{2\sqrt T}\sum_{t=1}^{T}(a_t-a_{t-1})

  \frac{a_T-a_0}{2\sqrt T}.
  ]

  So the apparent “composition of learned attributes” approximately collapses into a shrunken net displacement along the browsing path.
  That is not shared-pattern extraction.

  ## Three disconnected meanings of “learning”

   System              What it stores                                             What it affects
  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Local posterior     44D quadratic utility weights                              Next candidate planner
  ──────────────────  ─────────────────────────────────────────────────────────  ─────────────────────────────
   Persistent atlas    13 RGB/texture/symmetry statistics plus average actions    New-world initialization
  ──────────────────  ─────────────────────────────────────────────────────────  ─────────────────────────────
   Concept Shelf       Browser-local normalized action deltas                     Recast and lane labels only

  The atlas’s image representation is just color means/stds, saturation, edges, and flip symmetry in art-optimizer/art_optimizer/
  rendering.py:107. It cannot represent objects, motifs, subject identity, or sophisticated style. The renderer never receives its
  visual centroids or exemplars—only an average eight-dimensional action.

  The Concept Shelf controls do not influence ordinary next-candidate generation at all. They take effect only when Recast sends a
  composition New World request.

  The UI speaks as though these three systems form one coherent understanding. They do not.

  ## The UI “experiments”

  Your intuition was also correct here. The three concept interfaces share:

  - the same session ID;
  - the same backend state;
  - the same candidates;
  - the same learner and planner;
  - the same browser-local concept library.

  The differences are presentation, visibility, available buttons, and post-hoc candidate grouping. Lane Board does not ask the server
  for lane-specific candidates; it rearranges the same four candidates after generation.

  That is legitimate if the question is strictly “which presentation helps people understand the same system?” But they are views, not
  meaningfully different optimization experiments. There is no durable experiment_id, assignment, or treatment logging, and switching
  views contaminates any causal comparison.

  ## Real implementation defects found

  Beyond the conceptual problem:

  - Reroll updates active posterior/search state but not the current branch checkpoint. Restoring that same branch silently erases
    reroll learning.

  - Cancelling an asyncio.to_thread() render task cannot stop the underlying GPU call. Rapid commits/rerolls can leave stale work
    queued behind the renderer lock and create orphan artifacts.

  - State mutation, atlas evidence, next-round creation, and idempotency-result persistence are not one transaction. A crash between
    them can leave a committed mutation that cannot be safely retried.

  - The event log cannot reconstruct state; it is an audit log beside an authoritative JSON projection, not genuine event sourcing.
  - Candidate images and state accumulate without retention.
  - Concrete prompt-dependent embedding banks share one model-level control_basis_revision, allowing unvalidated numeric concepts/
    actions to transfer across prompts.

  ## What we did well

  We built a strong research apparatus:

  - Preview, commit, favorite, reroll, and New World have unusually clean distinct semantics.
  - The outside-option multinomial model is much better than four fake independent downvotes.
  - Exposure masking avoids learning from unseen or failed candidates.
  - Fixed seed and absolute coordinates make controlled comparisons possible.
  - Designs, worlds, and branch-local learner state are separated cleanly.
  - Branch restoration genuinely restores posterior and search snapshots.
  - Renderer, codec, learner, planner, atlas, and UI boundaries are modular.
  - Cache manifests and artifact writes are careful.
  - The documentation predicted nearly every failure observed and explicitly refused to claim the controls were validated.

  So the architecture was not foolish. Round 1 did its job: it falsified the optimistic interpretation cheaply.

  The mistake was crossing this line:

  instrumented hypothesis
  → product language implying visual understanding

  ## Simplest Round 2

  I recommend making it an honest coordinate optimizer first:

  1. Run fixed-seed sweeps across every axis, several prompts, and several seeds. Measure perceptual response, monotonicity, rank,
     correlation, duplicates, and artifacts.

  2. Whiten/calibrate the surviving control basis using the measured perceptual metric. Do not tune 0.24 or the radius blindly.
  3. Replace the 44-parameter quadratic learner initially with an eight-parameter preferred-target model:

  # [
  u(a\mid\theta)

  -\frac12(a-\theta)^TQ(a-\theta).
  ]

  Choice differences are linear in the eight unknown coordinates of (\theta), remain log-concave, and give an understandable “where the
  user currently wants to go” posterior.

  4. Expose the eight real authored axes—or call accepted deltas “saved moves.” Do not call them learned visual concepts.
  5. Make a lane provisional until it has repeated support across distinct anchors and seeds. Promote it only after held-out recasts
     demonstrate the same visual effect using image-delta embeddings.

  6. Split None of these from More variety.
  7. Treat Recast-current-action as the simplest “same controllable attributes, fresh realization” operation.

  If the desired product is genuinely:

  > click an image, retain its visual qualities, and generate a new descendant,

  then use a parent-conditioned image-editing pipeline and learn from visual-delta embeddings. That is a larger but honest product
  change.

  I audited all executable Python/JavaScript, tests, and governing specifications at 8f9c767. No files were changed. Verification: 35
  Python tests passed, the JavaScript concept test passed, and compilation passed. The normal local pytest invocation only lacked the
  optional pytest-timeout plugin; running without that configured option was clean.
