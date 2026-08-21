# Core Mechanics and User-Actions Design Review

**Reviewed contract:** [`docs/INTERACTION_MODEL_V0.md`](../docs/INTERACTION_MODEL_V0.md)  
**Reviewed product shape:** one committed full-canvas image, four corner candidates, preview, commit, reroll, favorite, New world, and recent history  
**Review goal:** decide whether each action has one understandable meaning, produces valid preference data, preserves agency, and composes cleanly with the branch and persistent-memory models

## 1. Executive verdict

The core interaction is unusually strong because it distinguishes actions that many systems collapse together:

```text
preview ≠ choose
choose ≠ favorite
reroll ≠ reset
reset ≠ dislike
restore ≠ regenerate
```

That separation is worth protecting.

The primary v0 action set should remain:

1. Preview candidate.
2. Commit candidate.
3. Reroll while keeping the anchor.
4. Favorite current or candidate.
5. Start a New world.
6. Restore a committed checkpoint.

Two actions should be added next:

7. Export/use with provenance.
8. Mark a render as broken or not judgeable, with zero preference effect.

The project should **not** add a generic dislike button yet. It would conflate several different failures and degrade the preference data.

The interaction is ready for implementation studies, but several state/data details should be corrected or experimentally resolved:

- explicit hover preview should not count as exposure instantaneously;
- proposal role must not be permanently confounded with screen corner or render order;
- internal role labels should remain hidden outside a debug mode;
- history restore should not automatically be treated as a strong taste endorsement;
- New-world root personalization needs one explicit semantic contract;
- global favorite behavior during full-canvas preview needs stronger visual clarity;
- four candidates and corner placement must be treated as hypotheses, not fixed truths.

## 2. Design principles

### 2.1 One action, one meaning

Every visible action should have one domain interpretation. The backend should not infer extra meanings from timing or pointer movement.

### 2.2 The current design is valuable

The user must never be forced to choose the least bad candidate. The committed design is an explicit outside option.

### 2.3 Navigation and taste are different

A design can be useful to continue from without being a final favorite. A design can be worth saving without being the branch the user wants to pursue.

### 2.4 Failure is not preference

Loading, low image quality, model artifacts, and missing candidates must not become negative aesthetic labels.

### 2.5 Creative risk requires recovery

Users should be able to make bold choices because every committed state is replayable and forkable.

### 2.6 Preference data must be earned

Only judgeable, exposed alternatives belong in the choice set. Passive dwell and feed-style engagement should not become reward.

## 3. Domain-action table

| Action | User meaning | Branch effect | Local preference | Persistent preference |
|---|---|---|---|---|
| Preview | inspect at full size | none | none | none |
| Commit | continue from this state | create next branch node | strong slate choice | weak positive |
| Reroll | keep anchor; replace alternatives | same branch/anchor, new round | weak anchor win | normally none |
| Favorite | remember this design | none | optional/none | strong positive |
| New world | new stochastic basin | new root and local reset | reset | preserve atlas |
| Restore | resume exact checkpoint | switch branch context | load old posterior | currently moderate revisit evidence |
| Export | use this artifact | none | optional | strongest positive |
| Broken render | not judgeable | exclude/replace candidate | none | none |

This table should remain the canonical semantics even when another UI—grid, feed, mobile app, or pairwise experiment—invokes the same commands.

# 4. Primary screen review

## 4.1 One full-canvas committed image

### Strengths

- reinforces that one design is evolving;
- gives every choice a visual baseline;
- supports the anchor outside option;
- feels more like editing than consuming a feed;
- preserves authorship and continuity;
- makes branch history meaningful.

### Risks

- the user compares full-size candidates serially and must remember previous previews;
- corner cards can occlude the artwork;
- small candidates may hide important detail;
- the visible current image can make candidate favorite targeting ambiguous during preview;
- loading overlays can compete with the artwork.

### Recommendation

**Keep as the default.** Add an experiment against a two-by-two full-image grid, but do not replace the immersive view without evidence.

The full-canvas system should support rapid reversible comparison:

- hover/hold a corner to preview;
- keyboard or gesture to move directly among previews;
- release/Escape to return to the exact committed image;
- clear `PREVIEW` versus `CURRENT` status;
- no crossfade long enough to obscure differences.

## 4.2 Four corner candidate cards

### Why four is plausible

- enough slots for four acquisition roles;
- manageable render cost;
- natural spatial memory;
- one richer observation than a binary duel;
- still small enough for a single screen.

### Why four is not settled

- two may be faster and less tiring;
- six may improve discovery on fast hardware;
- corner cards on a phone may become tiny;
- full-size preview is serial;
- choice overload depends on candidate similarity;
- a fixed count ignores variable rendering latency.

### Decision

**Keep four as the v0 default and explicitly A/B two, four, and six.**

The candidate count is a product parameter, even if the initial state model currently enforces four.

# 5. Preview review

## 5.1 Current meaning

Preview temporarily replaces the full-canvas display with a candidate but does not commit, add to history, update preference, or launch descendants.

This is correct and should remain a hard invariant.

## 5.2 Desktop

Hover is fast and discoverable. It also creates a subtle data problem: mouse movement through a corner can be accidental.

The current contract treats explicit preview as sufficient exposure. If `mouseenter` immediately marks a candidate exposed, a user can accidentally sweep through a card and later have that candidate included in a reroll or commit likelihood.

### Recommendation

Split preview display from exposure qualification:

```text
mouseenter
    display preview immediately

preview remains active for >= 250–300 ms
    mark meaningfully exposed

keyboard Space or intentional touch hold
    mark exposed when the hold threshold is reached
```

A committed or favorited candidate always counts as exposed.

This preserves immediate UI response without treating pointer transit as a judgment opportunity.

## 5.3 Touch

Tap-to-commit plus hold-to-preview is lean, but hold-to-preview is not naturally discoverable.

### Recommendation

Keep the semantics and add:

- one short onboarding cue the first time;
- haptic/visual transition when hold mode activates;
- slide-between-corners preview after hold;
- no hidden double-tap behavior;
- large candidate and star targets;
- an option to switch to first-tap-preview/second-tap-commit in a mobile experiment.

## 5.4 Keyboard

The normative commands are good:

- `1`–`4` commit;
- `Shift` + `1`–`4` preview;
- `Space` preview focused candidate;
- `Enter` commit;
- `Alt` + `1`–`4` favorite;
- `R`, `F`, `N`, `H`, `Escape`.

### Recommendation

Ship visible shortcut help. Hidden keyboard affordances do not count as accessibility.

# 6. Commit review

## 6.1 Meaning

Commit says:

> This is the most useful next state among the current design and the alternatives I meaningfully saw.

It does **not** necessarily say:

> This is beautiful, finished, or part of my durable taste.

The branch/persistent weight distinction is therefore correct.

## 6.2 Atomicity

The command should atomically bind:

- active round ID;
- chosen candidate ID and complete design state;
- anchor design;
- observed choice set;
- new branch node;
- learner snapshot;
- event and command receipt.

This makes retries safe and historical learning reproducible.

## 6.3 Partial rounds

Allowing commitment before all four candidates are ready is good. The user should not wait for a slow candidate that is irrelevant.

Only candidates with valid exposure should enter the likelihood. The chosen candidate is necessarily exposed.

## 6.4 Candidate arrival and position bias

This is a high-priority design-data issue.

If policy roles are always mapped to the same slots:

```text
top-left     best local
top-right    diverse
bottom-left  probe
bottom-right surprise
```

then policy quality becomes confounded with spatial bias.

If render scheduling also follows slot order, role becomes confounded with time-to-first-view. The first-ready image receives more exposure and may be chosen before later roles arrive.

### Recommendation

- randomize role-to-slot assignment per round;
- persist the assignment in round metadata;
- rotate or randomize render order independently;
- log ready timestamp, first visible timestamp, slot, role, and selection;
- preserve each slot's location only after that round's exposure begins;
- analyze role effects with inverse propensity or randomized assignment.

## 6.5 Role labels

The normative interaction contract says optimizer roles should not be shown in v0. The current browser implementation has displayed role text in candidate cards during development.

### Recommendation

Hide role labels in ordinary mode. Expose them only behind a debug/research flag.

Labels such as “local,” “probe,” and “surprise” can bias choice and destroy the very policy comparison being measured.

# 7. Reroll review

## 7.1 Current meaning

Reroll says:

> Keep the current design; none of the meaningfully exposed alternatives should replace it.

This is a clean outside-option observation.

## 7.2 RoundSkipped

When fewer than two candidates were judgeable, reroll should create no preference update. This is correct.

The event should distinguish:

```text
RoundRerolled
    valid weak anchor win

RoundSkipped
    insufficient judgeable alternatives
```

## 7.3 Behavioral ambiguity

Reroll can mean:

- all candidates are worse;
- candidates are too similar;
- candidates are fine but the user wants more;
- wrong type of variation;
- renderer quality problem;
- branch fatigue;
- accidental button press.

Therefore a 0.35-style low weight is a reasonable starting hypothesis, not a validated constant.

## 7.4 Recommendation

**Keep one reroll button.** Do not clutter the primary UI with several failure reasons.

After two or three consecutive rerolls, optionally offer a nonmodal reason strip:

```text
More different
Same direction, better options
Bad renders
Wrong direction
Just show more
```

Reason semantics:

- `Bad renders`: zero preference; replace candidates.
- `Just show more`: zero or very weak preference.
- `More different`: widen trust/novelty radius.
- `Same direction, better options`: retain direction, resample.
- `Wrong direction`: stronger local anchor win and/or mode switch.

The user may ignore the strip and continue with ordinary reroll.

## 7.5 Copy

“Reroll” is understandable from generative tools, but the actual meaning is “keep current and generate alternatives.” Tooltip/onboarding copy should say that explicitly.

# 8. Favorite review

## 8.1 Commit/favorite separation

This is one of the best design choices in the product.

A user can:

- favorite A because it is already compelling;
- commit B because it offers a more interesting route.

Collapsing those signals would damage both the branch learner and persistent memory.

## 8.2 Candidate favorite

The star is a separate hit target and must stop event propagation. Correct.

It can be used only after the candidate's complete replayable state exists. Correct.

## 8.3 Favorite-current during preview

The contract intentionally makes the global control target the committed design, not the image temporarily occupying the canvas.

This is logically consistent but visually risky. A user sees candidate B full-screen and may click the global star believing it targets B.

### Recommendation

During candidate preview:

- retain the candidate's own star in its card;
- change the global label to `☆ Favorite committed`;
- visually retain a small committed-design indicator;
- consider temporarily disabling the global star only if testing shows frequent mistakes.

Do not silently retarget the global star to the preview; that would make hover mutate the target of a durable command.

## 8.4 Is favorite really strong preference?

A star may mean:

- love it;
- save it for later;
- interesting reference;
- useful intermediate;
- do not lose it.

This is stronger than a commit but may not be as strong as export or repeated revisit.

### Recommendation

Keep favorite as strong evidence, but validate its weight against downstream behavior. Export/use should be stronger.

## 8.5 Unfavorite

Unfavorite should retract only the star contribution. It is not a negative label and should not delete the image or other evidence. Correct.

# 9. New-world review

## 9.1 Meaning

New world says:

> Keep my broad taste and conditions, but give me a different stochastic basin.

It is neither reroll nor dislike.

This separation is excellent.

## 9.2 What should persistence guide?

There are two coherent variants.

### Neutral-root variant

- new independent root noise;
- neutral action/root image;
- persistent atlas guides the first quartet.

Benefits:

- clean world origin;
- easy comparison of controls;
- root has no hidden mode choice.

Costs:

- first screen may feel unpersonalized;
- requires a root render plus candidates.

### Taste-guided-root variant

- new independent noise;
- root action/conditions initialized from an active atlas mode;
- quartet continues around that guided root.

Benefits:

- personalization appears immediately;
- fewer rounds to a compelling region.

Costs:

- “new world” also chooses a taste mode;
- a poor mode sample can look like a poor stochastic reset;
- root comparisons across worlds are less neutral.

The normative interaction document has described a neutral root, while implementations and earlier designs have experimented with atlas-biased initial actions. That ambiguity should be resolved.

### Recommendation

Use **taste-guided root by default**, because the user's request for New world is usually “another promising world,” not “show an unbiased benchmark.” Record the selected atlas mode and action explicitly.

Add later explicit variants:

```text
New world
Another side of my taste
Surprise me
Neutral world
```

Do not expose the menu until the base action has been studied.

## 9.3 Failure semantics

A New-world render failure must leave the previous world current and recoverable. Correct.

The command should not create negative evidence for the abandoned world, even if the user immediately resets again.

# 10. History and restore review

## 10.1 Last ten committed checkpoints

Showing committed states rather than all impressions is correct. It creates a creative history instead of a telemetry dump.

## 10.2 Cross-world clarity

A flat ten-image strip can obscure which items belong to different worlds.

### Recommendation

Add subtle structure:

- root marker or divider at New-world boundaries;
- current branch highlight;
- favorite star;
- optional branch/fork badge;
- no policy/utility scores.

## 10.3 Restore semantics

Restore should recover:

- world and stochastic root;
- committed design;
- model/codec/reference conditions;
- branch-local posterior;
- trust/search state;
- descendants without deleting them.

Correct.

## 10.4 Is restore persistent positive evidence?

The current design has treated restore as moderate persistent evidence because the image retained value after intervening choices.

This is plausible but not always valid. A user may restore to:

- compare;
- inspect a past state;
- recover from an accidental branch;
- continue because descendants failed, not because the design is a durable favorite.

### Recommendation

Reduce direct restore evidence. A stronger scheme is:

```text
restore only
    no or very weak persistent evidence

restore + commit descendant
    moderate revisit evidence

restore + favorite/export
    strong evidence
```

If restore remains a one-tap destructive navigation action, provide immediate Undo or retain the previous checkpoint in history.

## 10.5 Preview versus restore

A history hover/hold should be allowed to preview without restoring. Click/tap then resumes the checkpoint. This matches candidate preview semantics and avoids expensive accidental world restoration.

# 11. Export review

Export is the clearest missing first-class action.

## 11.1 Meaning

> This design has crossed from exploration into an artifact I intend to use, share, render at quality, or keep outside the session.

## 11.2 Effects

- no branch change by default;
- strongest persistent positive event;
- provenance bundle records model, codec, seed/noise identity, conditions, action, parent, and image digest;
- optional high-quality rerender is a separate output profile, not a new design state if semantics are unchanged.

## 11.3 Why it matters to research

Favorite is cheap and speculative. Export indicates higher commitment and should be the primary product-success event alongside later reopen/use.

# 12. Broken/not-judgeable review

A generated image can be technically ready but aesthetically unjudgeable because of:

- corruption;
- severe anatomy/text artifacts;
- safety filtering;
- blank output;
- reference failure;
- wrong model behavior.

Rerolling such a set currently risks creating preference evidence about the action rather than the renderer failure.

### Recommendation

Add a lightweight per-candidate or per-round command:

```text
Broken render / cannot judge
```

Effects:

- zero preference;
- candidate excluded from the slate observation;
- replacement requested in the same slot with a new candidate ID;
- quality telemetry logged separately;
- no persistent evidence.

This may live in a small overflow menu rather than the primary action bar.

# 13. Generic dislike review

A thumbs-down seems useful but is semantically underdetermined.

It may mean:

- dislike the image globally;
- dislike this change from the anchor;
- never show this style;
- bad quality;
- wrong subject;
- wrong branch;
- too much of one attribute;
- ordinary reroll.

### Decision

**Defer generic dislike.**

If negative preference is added, it should be explicit about scope:

```text
Avoid this artifact
Avoid this direction in this branch
Avoid this persistent style mode
```

These are advanced controls and should be supported only after enough data demonstrates a need.

# 14. Exposure review

## 14.1 Current threshold

A candidate qualifies through:

- durable ready asset;
- at least 50% visibility;
- at least 300 ms visible;
- or explicit preview/favorite/commit.

This is a good baseline.

## 14.2 Improvements

- require a short preview dwell before mouse hover counts;
- record ready and exposure timestamps;
- record viewport and slot;
- remove exposure when the document is hidden before threshold completion;
- never infer exposure from candidate existence;
- include explicit chosen candidate automatically;
- audit progressive-render first-ready effects.

## 14.3 Policy propensity

For offline evaluation, log:

```text
proposal policy revision
candidate role
hidden-pool rank
selection propensity or randomized assignment probability
slot
render order
```

Without this, the system can mistake its own exposure policy for user preference.

# 15. Loading and streaming review

Progressive slot streaming is valuable because it hides latency. It also creates decision bias.

### Risks

- first-ready candidates receive more attention;
- the user commits before seeing higher-latency roles;
- slot skeletons can look like unavailable options;
- role/slot/render-order correlation contaminates data;
- reroll before two ready candidates becomes a skip rather than a preference event.

### Recommendation

- randomize render order separately from slot;
- make loading state explicit but quiet;
- let the user commit early;
- show how many judgeable options are ready;
- disable preference-bearing interpretation until exposure threshold;
- compare sequential streaming with batch reveal in an experiment.

# 16. Candidate generation policy review

The four-role policy is interpretable and researchable. It should remain internal and be ablated.

### Required invariants

- candidates are distinct in action space;
- duplicate perceptual candidates are replaced before exposure when possible;
- no candidate silently changes world conditions;
- surprise remains bounded;
- at least one candidate is a credible continuation;
- all proposal metadata is durable.

### Potential improvement

Allow role allocation to change with context:

```text
first round / high uncertainty
    more probes and broad modes

several commits / low reroll rate
    more exploitation/refinement

repeated rerolls
    more diversity or mode escape

near export
    more local precision and quality
```

The UI count can remain four while the policy mixture changes.

# 17. Persistent evidence review

The initial evidence ordering is sensible:

```text
commit < restore/continue < favorite < export
```

But weights should be learned or tuned against held-out behavior, not treated as ontology.

### Recommended evidence ledger

| Event | Initial interpretation | Suggested v0 relative strength |
|---|---|---:|
| Commit | promising route | 0.03–0.08 |
| Reroll | local anchor win | 0 persistent |
| Restore only | navigation | 0–0.10 |
| Restore then continue | retained branch value | 0.20–0.35 |
| Favorite | durable save/taste | 0.75–1.00 |
| Export/use | final artifact value | 1.25–1.75 |
| Unfavorite | retract star contribution | negative of favorite event only |
| Broken render | system failure | 0 |

These are experimental ranges, not final constants.

# 18. Accessibility review

Required:

- minimum 44 CSS-pixel touch targets;
- keyboard focus visible on all candidate bodies and stars;
- role labels hidden but accessible candidate numbers present;
- screen-reader status for ready/failed candidates;
- reduced-motion mode;
- contrast-safe preview/current labels;
- no color-only favorite or current indicators;
- Escape returns to committed image;
- loading does not steal focus;
- history items have meaningful labels beyond “image.”

A creative research interface is not excused from accessibility because it is experimental.

# 19. Privacy and trust review

Persistent taste is sensitive behavioral data. The UI should eventually expose:

- whether persistent learning is enabled;
- what favorites and exports contributed;
- clear session reset versus persistent-memory reset;
- export of evidence and model state;
- deletion by design/session/all history;
- no use of hover/dwell as hidden reward;
- no cross-user collaborative learning without explicit consent.

This is especially important because “the system learned your taste” can be delightful or creepy depending on visibility and control.

# 20. Decision matrix

## Ship/keep

| Mechanic | Decision |
|---|---|
| One committed full-canvas image | keep |
| Four stable candidate slots | keep as v0 hypothesis |
| Hover/hold preview | keep; delay exposure qualification |
| Explicit commit | keep |
| Anchor-based reroll | keep at weak weight |
| Candidate/current favorite split | keep |
| New world separate from reroll | keep |
| Exact recent history and branching | keep |
| Meaningful-exposure choice set | keep |
| Hidden optimizer roles | enforce |

## Add next

| Mechanic | Reason |
|---|---|
| Export + provenance | strongest real-value event |
| Broken/not-judgeable | separates renderer failure from taste |
| History preview before restore | prevents accidental navigation/evidence |
| World dividers/root markers | improves branch comprehension |
| Shortcut/touch help | discoverability and accessibility |
| Debug-only policy overlay | research without biasing users |

## Experiment

| Question | Variants |
|---|---|
| Candidate count | 2 vs 4 vs 6 |
| Layout | corners vs 2×2 grid |
| Reveal | progressive vs batch |
| Reroll | weak outside option vs reason-assisted |
| New-world initialization | neutral vs taste-guided |
| History evidence | immediate vs continue-dependent |
| Noise | fixed vs correlated variants |
| Candidate roles | full policy vs ablations |
| Mobile commit | tap-commit vs tap-preview/tap-again |

## Defer

- generic dislike;
- visible learned mode names;
- direction sliders in primary browse mode;
- branch graph editor;
- collaborative/social feed;
- automatic generator fine-tuning;
- engagement-based reward;
- long-horizon RL.

# 21. Final design verdict

The primary interaction model is coherent and differentiated enough to justify implementation and study. Its strongest qualities are:

- one evolving anchor;
- explicit none-of-these behavior;
- commit/favorite separation;
- reroll/reset separation;
- exact recoverability;
- no hidden dwell reward.

The largest near-term risks are not missing buttons. They are **measurement confounds and semantic overreach**:

- role tied to slot;
- role tied to render order;
- accidental hover counted as exposure;
- history navigation treated as durable preference;
- favorite interpreted more strongly than users intend;
- New-world personalization left ambiguous;
- internal policy labels shown to users.

Fixing and testing those points matters more than adding another control panel. The product should remain small enough that each action keeps one crisp meaning.
