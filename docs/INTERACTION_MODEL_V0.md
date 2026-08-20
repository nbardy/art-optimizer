# Interaction Model V0

**Status:** Normative product contract  
**Last updated:** 2026-08-20

This document resolves the interaction questions that must not be left to incidental frontend implementation.

Where it conflicts with exploratory language in `UI_DESIGN.md`, this document governs v0 behavior.

## 1. Primary screen

The product displays:

```text
one committed full-canvas design
four stable corner candidate cards
Favorite current
Reroll
New world
last-ten history handle
```

The user should experience one design evolving, not a feed and not a control panel.

## 2. Three distinct image states

The frontend must distinguish:

```ts
type DisplayState = {
  committed: DesignView;
  preview: DesignView | null;
  candidates: CandidateView[];
};

const displayed = state.preview ?? state.committed;
```

- **Committed:** authoritative current branch state.
- **Previewed:** temporary full-canvas display of a candidate.
- **Candidate:** one of four possible descendants in the active round.

Preview never changes commitment, history, preference, descendants, or server branch state.

## 3. Candidate-card behavior

Each corner card has two explicit hit targets:

1. **card body** — preview on hover/hold; commit on click/tap;
2. **candidate favorite button** — favorite that candidate without committing it.

The candidate favorite button stops event propagation. Favoriting a candidate must never accidentally commit it.

The global `Favorite current` command always targets the committed design, even while a candidate is being previewed. Hover must not silently retarget a persistent action.

This deliberately preserves the distinction:

```text
commit = continue the branch from here
favorite = remember this as durable taste
```

A user may therefore favorite one candidate and commit another.

## 4. Desktop semantics

### 4.1 Hover

```text
pointer enters card body
→ candidate becomes full-canvas preview

pointer leaves card body
→ committed design returns
```

Hover:

- creates no preference observation;
- starts no descendant rendering;
- adds nothing to history;
- does not change the global favorite target;
- may emit sampled diagnostics only.

### 4.2 Click

Clicking a candidate card body commits the exact candidate currently associated with that card and round.

The full canvas itself is not a commit target. This avoids accidental commitment while inspecting a preview.

### 4.3 Fast pointer movement

Preview state is keyed by candidate ID and pointer/focus token. An old `previewEnded` event cannot clear a newer candidate preview.

## 5. Touch semantics

- tap card body: commit immediately;
- press and hold card body: temporary full-canvas preview;
- release after hold: restore committed design;
- slide between cards while holding: preview the card under the finger;
- tap candidate favorite button: favorite without commit;
- double tap: no special behavior;
- tap full canvas: no commit behavior.

All actionable targets must meet the platform's accessible touch-size requirement; v0 uses at least 44 CSS pixels for the candidate favorite target.

## 6. Keyboard semantics

- `1`–`4`: commit candidate;
- `Shift` + `1`–`4`: preview candidate while held;
- arrow keys: move candidate focus;
- `Space`: preview focused candidate while held;
- `Enter`: commit focused candidate;
- `Alt` + `1`–`4`: favorite candidate without committing;
- `F`: favorite current committed design;
- `R`: reroll;
- `N`: New world;
- `H`: open history;
- `Escape`: cancel preview or close overlay.

Keyboard help is discoverable in-product.

## 7. Commit semantics

When candidate \(j\) is committed:

1. validate the active round and candidate ID;
2. atomically make the candidate's complete `DesignState` current;
3. record one choice observation over the anchor plus meaningfully exposed candidates;
4. append the selected state to history;
5. clear preview state;
6. close the old round;
7. begin the next round from the selected absolute action;
8. cancel or demote stale speculative work.

A selection is branch-local evidence first and weak persistent evidence second.

## 8. Meaningful exposure

A valid choice set contains the current anchor and only candidates that were meaningfully exposed.

A candidate qualifies when:

- a valid preview asset was ready;
- at least half its card was visible;
- it was visible for at least 300 ms;
- or the user explicitly previewed, favorited, or committed it.

Failed, blocked, cancelled, or never-visible candidates are excluded.

Selection is allowed before all four candidates finish. The observation contains only the exposed alternatives plus the anchor.

## 9. Reroll semantics

Reroll means:

> Keep the current committed design; none of the exposed candidates was worth replacing it with.

When at least two candidates were meaningfully exposed, reroll records a weak outside-option observation with the anchor as winner.

When fewer than two candidates were meaningfully exposed, the command is recorded as `RoundSkipped`:

- no preference update;
- same parent remains current;
- a replacement round is requested;
- product telemetry may record that loading or presentation failed.

Reroll:

- never changes the world root;
- never downvotes the committed design;
- normally does not update the persistent atlas;
- modestly widens the local trust region;
- keeps prior rounds recoverable in the event log.

The button remains usable during rendering, but the server decides `RoundRerolled` versus `RoundSkipped` from exposure facts.

## 10. New world semantics

New world means:

> Start from a different stochastic root while retaining what the system knows about my broader taste.

It:

- stores the current committed design in history automatically;
- draws independent root noise;
- constructs a new world control basis;
- resets branch-local observations and search state;
- retains prompt, references, model profile, aspect ratio, favorites, and persistent atlas by default;
- creates a neutral root design;
- uses persistent modes when constructing the first quartet;
- applies no negative label to the previous world.

No confirmation dialog is required because the previous state remains recoverable. If unsaved local assets would actually be lost, the command is refused with an explanation rather than presenting a generic destructive dialog.

## 11. History semantics

The visible history contains the ten most recent committed design states across the active session, including world roots.

It does not contain:

- temporary previews;
- discarded candidates;
- candidate favorites that were never committed;
- failed renders.

The persistent backend retains the full immutable branch forest.

Selecting a history item:

1. restores its exact world, design state, local-posterior snapshot, and search snapshot;
2. makes it the committed design;
3. does not delete its existing descendants;
4. causes the next commit to create a new fork.

History restoration is moderate persistent evidence because the design retained value after intervening choices.

## 12. Favorites semantics

Two commands exist:

- `FavoriteCurrent(design_id)`;
- `FavoriteCandidate(round_id, candidate_id)`.

Both store the complete replayable design state and create strong persistent-atlas evidence.

Unfavorite retracts the favorite contribution only. It does not imply dislike and does not erase other evidence.

A candidate can be favorited only after a durable candidate state and preview asset exist. A still-queued placeholder cannot be favorited.

## 13. Conditions and model changes

V0 uses a simple rule:

> Any load-bearing generation-condition change starts a new world.

This includes:

- prompt or negative constraints;
- reference set or reference weights;
- model/checkpoint;
- aspect ratio;
- preservation locks;
- control-basis revision.

The old world remains in history. V0 does not attempt to reinterpret an existing branch under changed conditions.

A pure export-quality change that does not affect design semantics may rerender the same `DesignState` under a separate output profile.

## 14. Candidate slots

Slots remain spatially stable within the screen:

```text
1 top-left
2 top-right
3 bottom-left
4 bottom-right
```

Content never moves between slots after meaningful exposure begins. If a duplicate or failed candidate needs replacement, the replacement keeps the same slot and receives a new candidate ID.

The optimizer's role labels are not shown in v0. They remain metadata for debugging and evaluation.

## 15. Loading

Each slot streams independently:

```text
empty
→ queued
→ low-resolution preview ready
→ finalizing
→ final ready
```

A low-resolution candidate may be committed when:

- its full generative state is already durable;
- replay inputs are complete;
- the UI clearly indicates finalization is pending.

The committed state does not change when its higher-resolution asset arrives.

## 16. Failure behavior

### One candidate fails

- preserve the slot;
- show retry or replacement state;
- exclude the candidate from preference evidence.

### All candidates fail

- retain current design;
- show renderer error and retry/model-switch actions;
- do not infer reroll.

### Preference update fails

- keep using the previous immutable snapshot;
- continue interaction in degraded mode;
- never block a valid commit solely on learner failure.

### Client disconnects

- completed renders are not considered exposed until delivered after reconnect;
- stale rounds cannot overwrite active state.

## 17. What the UI does not infer

V0 assigns zero preference weight to:

- ordinary hover duration;
- pointer trajectory;
- page dwell time;
- loading delay;
- scroll position alone;
- speculative renders never shown;
- a closed browser tab.

These may be analyzed as product telemetry under a separate retention policy.

## 18. Interaction acceptance tests

1. hover/hold changes only `preview`;
2. leaving a preview restores the exact committed image;
3. card-body click commits;
4. candidate-star click never commits;
5. global favorite always targets committed state;
6. commit before all four are ready creates the correct exposed choice set;
7. early reroll with fewer than two exposed candidates creates `RoundSkipped`;
8. valid reroll preserves parent, world, and root noise;
9. New world preserves favorites and atlas but resets local state;
10. history restore reloads the correct local snapshot and forks on next commit;
11. fast pointer movement cannot display or restore the wrong candidate;
12. stale stream events cannot replace a newer slot or round;
13. failed candidates never become negative preference evidence;
14. touch, pointer, and keyboard produce equivalent domain commands.

## 19. Deferred interaction questions

The following do not block v0:

- user-visible names for persistent taste modes;
- explicit “another side of my taste” New-world modes;
- direction sliders and calibrated axis sweeps;
- branch graph visualization;
- explicit durable dislike/aversion controls;
- collaborative or social exploration;
- long-horizon novelty policies.

They must be introduced as new explicit commands rather than reinterpretations of existing events.
