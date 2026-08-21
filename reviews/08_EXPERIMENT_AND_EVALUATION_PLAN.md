# Experiment and Evaluation Plan

## 1. Purpose

Art Optimizer combines an interaction model, a preference learner, a candidate planner, persistent memory, and a generator control codec. A successful session cannot tell us which component helped. This plan decomposes the system into falsifiable experiments.

The evaluation order should be:

```text
interaction validity
    -> control-space validity
    -> local learning and planning
    -> persistent memory
    -> integrated creative value
```

Running a broad “do users like the app?” study before these layers are stable would produce anecdotes without diagnosis.

## 2. Primary outcomes

No single metric captures creative success. Use a portfolio.

### 2.1 Progress outcomes

- rounds to first commit;
- rounds to first favorite;
- rounds to first export;
- total generated candidates to favorite/export;
- session success rate: at least one favorite/export;
- fraction of sessions ending with the current design exported;
- time to first satisfactory artifact.

### 2.2 Preference-model outcomes

- held-out multi-choice negative log likelihood;
- top-choice accuracy;
- Brier/calibration score;
- posterior uncertainty calibration;
- regret under simulated utilities;
- recovery after one deliberately inconsistent choice;
- adaptation after a preference-mode switch.

### 2.3 Candidate-policy outcomes

- reroll rate;
- valid reroll versus RoundSkipped rate;
- within-slate perceptual diversity;
- duplicate/replacement rate;
- policy-role selection rate;
- first-ready and slot-position selection bias;
- percentage of probes that materially reduce posterior uncertainty;
- percentage of controlled-surprise candidates later favorited or revisited.

### 2.4 Agency and experience outcomes

Use short validated-style Likert items rather than one overall delight score:

- “I understood what each action would do.”
- “I felt in control of the direction.”
- “I could recover from an unhelpful choice.”
- “The system showed ideas I would not have prompted.”
- “The options became repetitive.”
- “Comparing the images was mentally tiring.”
- “The result feels like something I made.”
- “I would continue working with this branch.”

### 2.5 Artifact outcomes

- blinded preference between final artifacts from conditions;
- independent quality ratings;
- visual diversity across final artifacts;
- subject/identity preservation where relevant;
- actual later reopen, export, or use;
- provenance/replay success.

### 2.6 System outcomes

- root-render latency;
- first-candidate latency;
- all-four latency;
- candidate-arrival spread;
- peak VRAM;
- failed-render rate;
- stale-result cleanup rate;
- SSE reconnect recovery;
- command idempotency and version conflicts.

## 3. Instrumentation contract

Each candidate impression should record:

```text
session, world, branch, round
anchor design
candidate and design IDs
model/checkpoint/codec/control-basis revisions
absolute action and action blocks
policy and role
hidden-pool score/rank
slot
render scheduling order
render start/ready times
first visible time
visible fraction and qualified exposure time
preview start/end
commit/favorite/broken-render events
request and mutation versions
```

Every study condition must be stored in the event log. A screenshot of a UI setting is not sufficient provenance.

### 3.1 Privacy boundary

Record action events required for the experiment. Do not record raw pointer trajectories, unrelated page activity, or passive dwell as preference reward. Separate product telemetry from preference evidence.

## 4. Pre-experiment validity checks

Before human studies:

1. randomized role-to-slot assignment works and is persisted;
2. render order is independent of role and slot unless explicitly tested;
3. hidden role labels are disabled;
4. exposure qualification is stable under fast pointer movement;
5. stale HTTP/SSE snapshots cannot rewind the client;
6. failed and broken renders do not enter preference choices;
7. every artifact has replay/model/codec receipts;
8. simulated sessions can be reconstructed from events;
9. the same condition can be re-run from a fixed experiment seed;
10. data deletion and participant IDs are separated from public artifacts.

# 5. Experiment A: Candidate count

## Question

Is four the right number of alternatives for useful progress and manageable judgment?

## Conditions

- 2 candidates + anchor;
- 4 candidates + anchor;
- 6 candidates + anchor.

Keep total candidate-render budget equal where possible by limiting rounds, or report both per-round and per-render efficiency.

## Hypotheses

- two reduces fatigue but provides less information and diversity;
- six increases discovery but may increase decision time and skipped choices;
- four provides the best balance.

## Measures

- choice time after all candidates are exposed;
- rounds and renders to first favorite/export;
- reroll rate;
- within-slate diversity;
- self-reported cognitive effort;
- selection confidence;
- session completion.

## Decision gate

Keep four only if it is not dominated by both alternatives on progress per render and perceived effort. A small preference for four is insufficient if six produces substantially better artifacts at similar effort or two is equally effective at half the render cost.

# 6. Experiment B: Corner preview versus grid

## Question

Does one full-canvas image with corner candidates outperform a simultaneous two-by-two comparison?

## Conditions

### Immersive corner mode

- current image fills canvas;
- four corner thumbnails;
- hover/hold full-size preview.

### Grid mode

- four larger candidates visible simultaneously;
- current anchor visible in a fifth panel or toggle;
- click opens full-size inspection.

## Hypotheses

Corner mode improves continuity and authorship. Grid mode improves simultaneous comparison and reduces visual-memory load.

## Tasks

Use at least two task types:

1. open-ended exploration;
2. approach a described target/reference.

## Measures

- accidental commit rate;
- preview count and switching rate;
- choice time;
- ability to identify a previously previewed candidate;
- rounds to favorite/export;
- perceived continuity;
- mental comparison effort;
- final artifact preference.

## Decision gate

The default may differ by task or screen size. It is acceptable to retain immersive mode for open-ended work and grid mode for comparison-heavy refinement.

# 7. Experiment C: Preview and exposure semantics

## Question

When should a preview count as meaningful exposure?

## Conditions

- immediate on pointer entry;
- after 250 ms continuous preview;
- after 500 ms continuous preview;
- only explicit keyboard/touch preview or card visibility threshold.

## Measures

- number of accidentally exposed candidates;
- mismatch between self-reported seen candidates and event log;
- model choice-likelihood calibration;
- fast pointer transit rate;
- commit/reroll choice-set size.

## Decision gate

Select the shortest threshold that keeps false exposure below an agreed pilot threshold while not excluding candidates participants report comparing.

# 8. Experiment D: Progressive versus batch reveal

## Question

Does streaming candidates as they finish save useful time or bias decisions toward early results?

## Conditions

- progressive independent reveal;
- batch reveal after all candidates are ready;
- progressive reveal with a brief “more arriving” commit delay;
- progressive reveal with randomized render order.

## Measures

- first-ready selection rate;
- selection as a function of exposure duration;
- time to action;
- abandonment during generation;
- policy-role selection adjusted for arrival order;
- final artifact quality/preference.

## Decision gate

Keep unrestricted progressive commitment only if early-arrival bias is small or does not reduce outcome quality. Otherwise retain streaming preview but delay preference-bearing commit until a minimum judgeable set exists.

# 9. Experiment E: Reroll semantics

## Question

What does reroll mean behaviorally, and how much preference weight should it receive?

## Conditions

- anchor win weight 0.0;
- weak weight 0.15;
- current weight 0.35;
- higher weight 0.7;
- weak weight plus optional reason strip after repeated rerolls.

## Ground-truth probe

After sampled rerolls, ask a nontraining research question:

```text
Why did you reroll?
all worse / too similar / wrong kind of change / bad renders / just wanted more / other
```

Do not ask every time; that changes the product.

## Measures

- next-round selection rate;
- model held-out choice likelihood;
- trust-radius change effectiveness;
- repeated reroll count;
- reason distribution;
- false persistent drift;
- user frustration.

## Decision gate

Use the weight that improves held-out local choices without turning “just more options” or bad renders into strong negative direction evidence.

# 10. Experiment F: New-world initialization

## Question

Should a New world begin at a neutral action or a taste-guided root?

## Conditions

- independent root noise, neutral action;
- independent root noise, active atlas-mode action;
- independent root, alternate taste mode;
- independent root, outside-prior surprise.

## Measures

- first-root favorite rate;
- rounds to first commit/favorite/export;
- immediate second reset rate;
- mode coverage;
- perceived personalization;
- perceived novelty;
- cross-world artifact diversity.

## Decision gate

Use taste-guided default only if it reduces time to value without collapsing worlds into a narrow recurring aesthetic. Maintain explicit outside-prior mass.

# 11. Experiment G: Fixed seed/noise strategy

## Question

Does a fixed stochastic root improve local learnability without reducing useful diversity?

## Conditions

1. fixed materialized noise within world;
2. correlated variation \(\rho\approx0.98\);
3. moderate correlated variation \(\rho\approx0.8\);
4. independent seed per candidate;
5. factorial semantic-direction/noise-variant slates.

## Measures

- action-to-image smoothness;
- within-slate diversity;
- subject/composition preservation;
- preference-model predictive accuracy;
- rounds to favorite/export;
- user reports of “all too similar” versus “completely unrelated.”

## Decision gate

Choose the smallest stochastic variation that materially improves discovery without making the action utility nonstationary or unlearnable. It may be task-specific.

# 12. Experiment H: Model-control codec validation

## Question

Do the eight prompt-embedding axes provide a smooth, useful control basis for FLUX and Krea?

## Conditions

For each model:

- prompt-string compilation;
- prompt-embedding directions;
- random orthogonal embedding directions;
- seed/noise-only baseline;
- later reference-weight and adapter controls.

## Sweep design

For each of at least several prompts and roots, render:

\[
\alpha\in\{-1,-0.5,0,0.5,1\}
\]

for every coordinate.

## Automatic measures

- perceptual distance versus step size;
- adjacent/distant similarity ratio;
- image-text axis classification;
- unrelated-attribute drift;
- identity/composition preservation;
- coordinate redundancy and Jacobian condition number;
- artifact rate.

## Human measures

- axis direction recognizability;
- monotonicity judgment;
- useful amount range;
- preference-search progress;
- perceived controllability.

## Decision gate

A coordinate enters the supported basis only if it is responsive, reasonably smooth, nonredundant, and useful across its declared scope. FLUX and Krea receive separate decisions.

# 13. Experiment I: Candidate planner ablation

## Question

Does the four-role policy outperform simpler slate policies?

## Conditions

- random local perturbations;
- top-four posterior mean;
- four Thompson samples;
- mean + diversity;
- uncertainty + diversity;
- full role-balanced policy;
- full policy without persistent guidance;
- full policy without controlled surprise.

## Simulated utilities

Test first on:

- linear utility;
- quadratic utility;
- sparse coordinate utility;
- multimodal utility;
- drifting utility;
- inconsistent/cyclic comparisons;
- generator-surrogate utility from image features.

## Human measures

- rounds/renders to favorite/export;
- reroll rate;
- repetition;
- discovery ratings;
- final artifact preference.

## Decision gate

The role-balanced planner should earn its complexity through progress or discovery. If a simpler Thompson-plus-diversity policy performs equivalently, use the simpler policy.

# 14. Experiment J: Local preference model

## Conditions

- no learner/random walk;
- current quadratic Bayesian linear model;
- linear-only Bayesian model;
- pairwise/multi-choice GP;
- random-feature nonlinear model;
- recency/no-recency variants.

## Measures

- held-out choice likelihood;
- calibration;
- wall-clock update/proposal latency;
- numerical stability;
- simulated regret;
- human session progress;
- recovery after preference switch.

## Decision gate

Prefer the simplest learner within a practically insignificant margin of the best human outcome. Model-likelihood gains alone do not justify a slower or less understandable system.

# 15. Experiment K: Persistent preference representation

## Question

Does persistent memory help new worlds and sessions without narrowing exploration?

## Conditions

- no persistent memory;
- weighted mean favorite embedding;
- online multimodal atlas;
- exemplar retrieval without clustering;
- sequence-conditioned preference prior;
- collaborative/content hybrid when multi-user data exists.

## Longitudinal protocol

Participants complete multiple sessions on different prompts over several days. Later sessions include:

- a related prompt;
- an unrelated prompt;
- an invitation to revisit an older style;
- an open-ended New-world task.

## Measures

- rounds to first favorite/export in later sessions;
- retrieval of held-out favorites;
- mode diversity;
- repeated-aesthetic rate;
- outside-prior selection success;
- user recognition of learned taste;
- perceived creepiness/control;
- ability to disable/delete memory.

## Decision gate

Persistent memory must reduce cold-start effort while preserving mode diversity and user trust. A memory model that improves immediate clicks but collapses exploration fails.

# 16. Experiment L: Persistent event weights

## Question

How strongly should commit, restore, favorite, and export affect the atlas?

Use future behavior as supervision:

- later revisit;
- export;
- repeated favorite;
- selection in a cross-session comparison;
- manual mode assignment.

Fit or cross-validate event weights rather than treating initial values as fixed truth.

Test restore evidence variants:

- immediate moderate evidence;
- weak evidence;
- evidence only after continuing the branch;
- evidence only after favorite/export.

# 17. Experiment M: Branch recoverability

## Question

Does exact history increase exploration and reduce regret?

## Conditions

- visible exact history/forking;
- linear undo only;
- no history during task, restored afterward.

## Measures

- distance/risk of committed actions;
- number of forks;
- return rate;
- accidental branch regret;
- perceived safety and control;
- final artifact quality;
- session duration without engagement optimization.

## Decision gate

History should remain even if it does not directly improve final quality, provided it materially improves agency and does not create major interface complexity.

# 18. Simulated-user testbench

Human studies are too expensive for basic optimizer bugs. Build deterministic simulated users.

## Utility families

### Linear

\[
f(a)=w^\top a.
\]

### Quadratic

\[
f(a)=w^\top a+a^\top Qa.
\]

### Multimodal

\[
f(a)=\log\sum_k\pi_k\exp\left(-\frac{1}{2}(a-\mu_k)^\top\Sigma_k^{-1}(a-\mu_k)\right).
\]

### Image-feature surrogate

\[
f(a)=g(\phi(G(a))).
\]

### Drifting

Switch or interpolate utility modes after a fixed round or after exposure to a novelty region.

## Choice noise

Sample choices through the same multinomial likelihood used by the product, with variable temperature and occasional lapses.

## Infrastructure noise

Simulate:

- missing candidates;
- progressive arrival;
- accidental exposure;
- render artifacts;
- stale commands;
- restart recovery.

## Required baselines

- random search;
- greedy local search;
- seed-only browsing;
- top-four mean;
- Thompson sampling;
- diversity-only;
- oracle optimizer where available.

# 19. Human-study program

## Pilot 1: comprehension and usability

Small formative study. Think-aloud permitted.

Questions:

- Do users distinguish preview, commit, and favorite?
- What do they think reroll and New world mean?
- Can they recover a branch?
- Do mobile users discover hold-to-preview?

Do not interpret this pilot as performance evidence.

## Pilot 2: controlled within-subject comparison

Compare two or three high-priority UI/algorithm conditions. Counterbalance order and prompts. Use fixed render budgets.

## Study 3: open-ended creative sessions

Longer tasks with participant-selected themes. Measure exports, branch behavior, authorship, and discoveries.

## Study 4: longitudinal persistence

Multiple sessions over days/weeks. Evaluate atlas value, mode diversity, memory controls, and trust.

## Study 5: expert workflow

Artists/designers use the system for a real brief. Capture integration with external tools, provenance needs, refinement actions, and whether the output is actually used.

# 20. Statistical analysis

- preregister primary outcomes for confirmatory studies;
- use within-subject designs where learning/carryover can be controlled;
- include participant and prompt random effects;
- report confidence intervals and raw distributions;
- correct or hierarchically model multiple comparisons;
- distinguish per-round, per-render, and per-minute efficiency;
- report missing/failed renders by condition;
- do not substitute interaction count for creative value;
- publish null or negative results for core hypotheses.

Sample size should be chosen from pilot variance and a declared minimum effect of practical interest, not a generic fixed number.

# 21. Decision dashboard

A release candidate should answer:

| Layer | Gate |
|---|---|
| Interaction | users understand actions; accidental commitments/exposures are low |
| Codec | enough smooth, useful, nonredundant dimensions under declared scope |
| Local learner | improves held-out choices and/or progress over simple baselines |
| Planner | role policy earns value over a simpler policy |
| Persistent atlas | reduces later cold-start without collapse |
| Recovery | branches replay across restarts and model revisions |
| System | latency supports the interaction on target hardware |
| Trust | memory and provenance are visible and controllable |

# 22. Immediate experiment order

1. Hide policy role labels; randomize role-to-slot and render order.
2. Validate exposure timing with a small comprehension pilot.
3. Run FLUX/Krea coordinate sweeps under fixed roots.
4. Compare prompt-string and embedding codecs.
5. Run simulated planner/learner ablations.
6. Compare four-corner and grid interfaces.
7. Add export and broken-render actions.
8. Run first end-to-end human comparison against prompt/seed browsing.
9. Only then begin longitudinal atlas evaluation.

This sequence minimizes the chance of training or studying a sophisticated preference system on invalid interaction data.
