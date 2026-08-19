# UI Design

**Status:** Proposed MVP interaction contract  
**Last updated:** 2026-08-19

## 1. Product objective

Art Optimizer should feel like continuously shaping **one design**, not operating a recommender feed and not tuning a wall of latent sliders.

The main canvas always represents one committed design state. Four small alternatives occupy the corners. A pointer hover or touch hold temporarily previews an alternative at full size; a click or tap explicitly commits it. The machine learns from the sequence of choices while keeping enough state to replay, fork, and compare every committed step.

The primary loop is:

```text
current committed design
        ↓
four proposed descendants
        ↓
preview any descendant at full size
        ↓
pick one ───────────────→ commit it and generate four children
reroll ─────────────────→ keep the current design and propose four more
star ───────────────────→ preserve durable preference evidence
new world ──────────────→ change the stochastic root, retain broader taste
history ────────────────→ restore and fork from a prior committed design
```

## 2. Product principles

### 2.1 One canvas, one committed truth

Only one design is committed at a time. Candidate previews may temporarily replace the displayed pixels, but they do not alter the branch until selection.

```ts
committedDesign: DesignState;
previewDesign: DesignState | null;

displayedDesign = previewDesign ?? committedDesign;
```

This distinction prevents accidental pointer movement from becoming a preference label or invalidating generation work.

### 2.2 Selection means “continue from here,” not merely “like”

A user may choose an imperfect candidate because it opens an interesting path. Selection is therefore strong **branch-local comparative evidence**, but only moderate long-term taste evidence.

### 2.3 A star means “keep this as part of my taste”

Starring is independent of navigation. The user can star the committed image or a candidate without necessarily branching from it. A star is strong persistent evidence and places the design in a durable favorites collection.

### 2.4 Reroll is an outside option

Reroll means that no displayed candidate was compelling enough to replace the current design. It is weak negative evidence about the quartet, not a command to forget the current branch.

### 2.5 New world is exploration, not rejection

New world draws a new initial-noise root and begins a new local search. It does not downvote the previous design or erase persistent taste.

### 2.6 History is a forgiving branch interface

The visible last-ten history is a compact view. Internally, every committed design belongs to an immutable branch tree. Restoring an old design creates a fork instead of rewriting history.

## 3. Desktop layout

```text
┌──────────────────────────────────────────────────────────────┐
│  [prompt / references / model ▾]                 [session ⋯] │
│                                                              │
│  ┌─────────┐                                      ┌─────────┐│
│  │    1    │                                      │    2    ││
│  │ preview │                                      │ preview ││
│  └─────────┘                                      └─────────┘│
│                                                              │
│                                                              │
│                  CURRENT OR HOVER PREVIEW                    │
│                        FULL CANVAS                            │
│                                                              │
│                                                              │
│  ┌─────────┐                                      ┌─────────┐│
│  │    3    │                                      │    4    ││
│  │ preview │                                      │ preview ││
│  └─────────┘                                      └─────────┘│
│                                                              │
│         ☆ Favorite       ↻ Reroll       ✦ New world          │
│                  ───── last ten handle ─────                  │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 Main canvas

The main canvas uses the largest feasible area while preserving the design’s aspect ratio. Letterboxed regions may carry subtle controls, but the image itself should not be cropped merely to fill the viewport.

The canvas displays one of:

- the committed design;
- a temporary candidate preview;
- a deterministic loading transition from a low-resolution preview to the final render;
- an explicit recoverable error state.

### 3.2 Candidate overlays

Each candidate overlay should:

- occupy roughly 14–20% of the shorter viewport dimension on desktop;
- preserve the candidate aspect ratio;
- remain large enough to judge composition at a glance;
- gain a clear focus/hover border and slot number;
- expose render progress without shifting position;
- avoid hiding controls that belong to the underlying design;
- fade to reduced opacity after inactivity and restore on pointer movement or keyboard focus.

The four slots remain spatially stable across rounds. Stable placement lowers visual search cost, while candidate content changes.

### 3.3 Bottom command row

The primary command row contains:

- **Favorite** — stars the currently displayed design; while previewing, the label clarifies whether the candidate or committed design will be starred;
- **Reroll** — rejects the current quartet softly and keeps the committed state;
- **New world** — starts from a new root-noise state after a brief undoable transition;
- a collapsed **history handle** — reveals the last ten committed states.

The row should never obscure candidate overlays or rely on unlabeled icons alone.

### 3.4 Prompt and conditions drawer

The main experience is visual, but users still need to establish initial conditions. A collapsed top drawer contains:

- prompt or concept text;
- optional negative constraints where supported;
- reference images and their weights;
- aspect ratio and target resolution;
- model/checkpoint selection;
- preservation locks such as subject, layout, palette, or style;
- advanced controls behind a second disclosure.

Changing a load-bearing condition creates a new branch context. The UI must say whether the current design can be reinterpreted under the new conditions or whether a new world is required.

## 4. Interaction contract

## 4.1 Hover preview on desktop

```text
pointer enters candidate 2
        ↓
previewDesign = candidate 2
        ↓
main canvas crossfades to candidate 2
        ↓
pointer leaves candidate 2
        ↓
previewDesign = null
        ↓
main canvas returns to committed design
```

Hover does not:

- commit a state;
- update the optimizer;
- add to history;
- generate descendants;
- downvote other candidates.

Hover duration may be logged for interface diagnostics, but it should have zero or negligible preference weight in the MVP.

### 4.2 Click commit on desktop

Clicking the hovered or focused candidate:

1. atomically commits the candidate’s full generative state;
2. appends it to the visible history;
3. records one four-way selection event;
4. marks the other genuinely exposed candidates as alternatives in the same choice event;
5. clears preview state;
6. cancels or deprioritizes stale speculative jobs;
7. begins streaming four descendants of the new committed state.

The click target remains the corner card even while the candidate is displayed at full size. The canvas itself should not ambiguously commit on click.

### 4.3 Touch behavior

Touch has no hover, so use:

- **tap candidate:** commit immediately;
- **press and hold:** preview at full size while held;
- **release after hold:** restore the committed image;
- **slide finger between corners while holding:** preview each candidate without committing;
- **double tap:** no special meaning in the MVP, avoiding accidental branches.

A short haptic tick may acknowledge commit where platform support exists.

### 4.4 Keyboard behavior

- `1`, `2`, `3`, `4`: commit the corresponding candidate;
- hold `Shift` + `1`–`4`: preview while held;
- arrow keys: move focus between candidate cards;
- `Enter`: commit focused candidate;
- `Space`: preview focused candidate while held;
- `R`: reroll;
- `F`: favorite displayed design;
- `N`: new world;
- `H`: open history;
- `Escape`: cancel preview or close a drawer.

All commands must be discoverable in a keyboard-help overlay.

## 5. User-action semantics

| Action | Navigation effect | Local preference update | Persistent preference update |
|---|---|---:|---:|
| Commit candidate | Candidate becomes current | Strong comparative positive | Small positive |
| Star design | None unless separately selected | Optional positive | Very strong positive |
| Reroll | Keep current design | Weak outside-option evidence | Usually none |
| New world | New root and local model | Reset branch-local posterior | Preserve persistent prior |
| Restore history | Restore and fork | Reopen prior branch context | Moderate revisit signal |
| Export | None | Moderate positive | Extremely strong positive |
| Hide/dislike | None | Strong negative | Strong negative when explicit |
| Hover/hold | Temporary preview only | None in MVP | None |

The event log records the action and its exposure context; the optimizer decides how to weight it. UI code must not silently convert hover, loading delay, or viewport time into definitive preference labels.

## 6. Reroll behavior

Reroll keeps the committed state and the branch’s materialized root noise. It requests a new slate with a modestly larger search radius or higher exploration coefficient.

Repeated rerolls can widen search gradually:

$$
r_{k+1}=\min(r_{\max},\gamma r_k), \qquad \gamma>1.
$$

The UI may show a quiet progression label after repeated rerolls:

```text
Nearby → Broader → Wilder
```

It must not silently change the world/root noise. A distinct New world action owns that semantic change.

Reroll should remain available while some candidates are still rendering. The action applies to the current round identifier, and late results from that round are discarded from the visible UI.

## 7. New-world behavior

New world creates a new root state while retaining:

- account-level favorites;
- persistent user-interest representations;
- current prompt and references unless the user changes them;
- model and output settings;
- the prior world in history/favorites.

It resets:

- branch-local comparisons;
- local trust-region center;
- cumulative local control action;
- root initial-noise tensor;
- speculative descendants.

Before switching, the current committed state is automatically recoverable from history. A destructive confirmation dialog is unnecessary unless unsaved local-only assets would be lost.

## 8. History and branches

### 8.1 Visible history

The last-ten strip contains the ten most recent **committed** designs, not previews and not every candidate shown.

Each tile displays:

- thumbnail;
- branch/fork marker when relevant;
- star marker;
- current-state marker;
- render or provenance warning if replay is unavailable.

Selecting a history tile restores its exact state and starts a new fork when the next candidate is committed.

### 8.2 Underlying branch tree

The backend retains the complete tree:

```text
root A
└── B
    ├── C
    │   └── D
    └── E
        ├── F
        └── G
```

The MVP can expose only the last-ten strip. A later branch-map view may show the full tree, comparisons between siblings, and named checkpoints.

### 8.3 Favorites

Favorites are durable and cross-session. A favorite stores the complete design state and rendered asset, not just an image URL.

A favorite may be used later as:

- a persistent taste signal;
- a reference image;
- a new branch anchor;
- a component in a multi-interest user representation;
- offline adapter-training evidence, with explicit user consent.

## 9. Candidate roles

The four candidates should not be the four highest-scoring near-duplicates. A default slate has explicit roles:

1. **Best local continuation** — highest posterior expected utility near the current design;
2. **Best diverse continuation** — high utility with a diversity constraint against slot 1;
3. **Informative probe** — high posterior uncertainty or information gain;
4. **Controlled surprise** — farther from the current state or informed by a different persistent interest mode.

The product need not label these roles. They are proposal-policy metadata used for debugging and evaluation.

When the optimizer is uninitialized, the roles become deterministic exploratory perturbations in separate control subspaces.

## 10. Loading and latency

### 10.1 Streaming

Each slot is independent. A candidate appears as soon as its preview render is available; the UI does not wait for all four.

A slot progresses through:

```text
queued → preview rendering → preview ready → finalizing → ready
```

The user may select a preview-ready candidate before high-resolution finalization if the state is already deterministic and replayable.

### 10.2 Speculative generation

While a round is visible, the backend may speculatively render descendants for candidates with high estimated selection probability. A committed selection can therefore yield immediate cached children.

Speculation must never alter preference data. It is a latency optimization only.

### 10.3 Stale results

Every generation job carries:

- session ID;
- branch version;
- parent design ID;
- round ID;
- slot ID;
- proposal ID.

The client ignores results that do not match its active round. The backend may still retain them for cache or research purposes if policy permits.

## 11. Error states

A failed candidate render occupies its original slot and offers an unobtrusive retry. It is excluded from preference comparisons unless the user explicitly interacted with a valid preview.

If all four fail:

- keep the committed design visible;
- explain the renderer failure;
- offer retry and model switch;
- do not record a reroll or downvote automatically.

If deterministic replay fails because a model revision is unavailable, history still shows the stored rendered asset and marks the state as non-rerenderable.

## 12. Accessibility

The UI must support:

- full keyboard control;
- visible focus states;
- screen-reader labels announcing candidate number, render status, and commit semantics;
- reduced-motion mode that replaces crossfades with immediate swaps;
- high-contrast candidate boundaries;
- zoom without hiding selection controls;
- configurable overlay size;
- no reliance on color alone for current, favorite, or failed states.

Alternative text for generated designs is useful for navigation but must be clearly machine-generated and must not claim certainty about ambiguous content.

## 13. Event instrumentation

Every candidate impression records:

```text
candidate_id
round_id
slot
proposal_policy
proposal_probability
viewport_visibility
preview_ready_at
visible_duration
preview_count
commit/star/reroll outcome
client and model revisions
```

The proposal probability or a reconstructable proposal distribution is required for later off-policy evaluation. Rank and exposure are confounders; a candidate cannot be treated as rejected if it never rendered or was never meaningfully visible.

## 14. MVP acceptance criteria

The first UI slice is complete when:

1. one committed design fills the canvas;
2. four stable corner cards stream independently;
3. hover/hold preview never mutates committed state;
4. click/tap commit is atomic and exactly replayable;
5. reroll preserves current state and records an outside-option event;
6. star persists complete design state without forcing navigation;
7. new world changes the root-noise state without downvoting the old world;
8. the last ten committed designs can be restored and forked;
9. stale generation results cannot overwrite a newer round;
10. keyboard and touch flows are covered by automated interaction tests.

## 15. Deferred interface ideas

The following are intentionally outside the first interaction loop:

- named semantic sliders;
- a full branch graph;
- social or collaborative feeds;
- natural-language explanations of learned taste;
- automatic per-click model fine-tuning;
- multi-user rooms;
- public galleries;
- long-horizon engagement optimization.

They may become useful later, but none should compromise the clarity of the one-design/four-candidate loop.
