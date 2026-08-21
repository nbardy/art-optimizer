# Concept Lanes: Executable UI Experiment Specification

**Status:** implementation and evaluation contract  
**Date:** 2026-08-22  
**Companion:** [From Image Anchors to Composable Concept Lanes](09_ATTRIBUTE_LIBRARY_AND_ANCHORING_EXPLORATION.md)

## 1. Purpose

This experiment tests a narrow question before changing the core optimizer:

> Can ordinary four-way choices produce a useful library of reusable, non-prompt visual directions, and how much of that library should the interface expose?

The implementation intentionally reuses the same backend and domain actions. Differences between interfaces should therefore be attributable primarily to presentation and concept interaction, not to different renderers or preference models.

## 2. Experiment registry

The server exposes four interfaces:

| ID | Route | Role |
|---|---|---|
| `current-image` | `/ui/current-image` | baseline |
| `implicit-lanes` | `/ui/implicit-lanes` | low-burden treatment |
| `concept-shelf` | `/ui/concept-shelf` | explicit-composition treatment |
| `lane-board` | `/ui/lane-board` | structure-visible treatment |

The process default is selected with:

```bash
ART_OPTIMIZER_UI=implicit-lanes python -m art_optimizer.app
```

The registry is available from `GET /api/ui-experiments`.

Every experimental UI uses the same session endpoints, SSE stream, generated assets, renderer, Bayesian choice learner, candidate planner, persistent atlas, branch history, and optimistic mutation version.

## 3. Shared modules

The three new clients are thin compositions of shared modules:

```text
experiment_core.js
    session lifecycle
    SSE and stale-snapshot rejection
    HTTP commands
    exposure set
    concept library
    concept composition

experiment_components.js
    candidate card
    hover/hold preview
    favorite target
    exposure tracker
    concept card
    history strip
    experiment switcher

experiment_styles.css
    shared visual tokens
    responsive layouts
```

Each UI file is responsible only for layout-specific projection:

```text
ui_implicit.js
ui_shelf.js
ui_lanes.js
```

No interface reimplements the preference learner, concept math, command semantics, or candidate-card gesture logic.

## 4. Experimental concept data model

The first implementation stores concept state in browser local storage:

```ts
type ConceptScope = {
  dimension: number;
  nextLabel: number;
  concepts: ConceptLane[];
};

type ConceptLane = {
  conceptId: string;
  label: string;
  direction: number[];
  magnitude: number;
  strength: number;
  support: number;
  opposition: number;
  activation: "auto" | "on" | "off";
  exemplarImageUrl: string | null;
  exemplarDesignId: string | null;
  createdAt: string;
  updatedAt: string;
};
```

Scopes are keyed by `control_basis_revision`. This prevents numeric directions learned under Krea from being applied to FLUX or to a later incompatible codec revision.

This is a deliberate experiment boundary:

- all three UIs share concept state in one browser;
- the production session database is not migrated before the interaction is validated;
- deleting browser storage deletes the experimental concepts but not authoritative session history or favorites;
- the concept library is not yet collaborative or available on another device.

## 5. Automatic learning events

### Commit

A commit computes the accepted delta from the pre-command snapshot. The normalized delta is merged into the nearest sufficiently aligned lane or creates a new lane. It receives one positive-support unit.

### Reroll

A reroll with at least two exposed candidates gives weak opposition to lanes strongly aligned with the rejected candidate deltas. An underexposed skip gives no concept evidence.

### Favorite

Favorite remains durable image/mode evidence for the existing persistent atlas. It does not automatically create a direction, because an isolated favorite does not identify which change caused its value.

### Restore

History restore changes the active realization but does not edit concept evidence. Continuing from a restored design can subsequently create new lane evidence through ordinary commits.

## 6. Composition and reset operations

The backend `NewWorldPayload` now supports:

```json
{ "mode": "taste_guided" }
```

```json
{ "mode": "neutral" }
```

```json
{
  "mode": "composition",
  "target_action": [0.1, -0.2, 0.0, 0.4, 0.1, 0.0, -0.1, 0.2]
}
```

All three operations create a new seed and reset branch-local preference state. They differ only in the initial absolute action:

- **taste-guided:** existing persistent-atlas initialization;
- **neutral:** control-space origin;
- **composition:** exact validated active concept composition.

The old world remains recoverable in history. Composition reset is not a negative label on the previous image.

## 7. Interface A — Implicit lanes

### Layout

- full-canvas committed image;
- four corner candidates;
- original preview/commit gestures;
- small lane-status indicator;
- optional concept drawer;
- primary `Recast learned mix` action.

### Intended user model

> Keep choosing images. The system quietly remembers reusable aspects. Recast when the image itself has become the wrong container for those aspects.

### Primary hypothesis

Implicit lane learning plus one recast command captures most of the benefit without materially increasing interaction burden.

### Failure signal

Users cannot predict what recast will preserve, or do not discover the lane drawer/status at all.

## 8. Interface B — Concept shelf

### Layout

- large current/preview image;
- 2×2 candidate grid;
- always-visible concept shelf;
- exemplar thumbnail, auto/on/off state, evidence, and amount per lane;
- explicit neutral, composition-recast, and taste-guided reset choices.

### Intended user model

> Images are realizations. The shelf is the composition I am building.

### Primary hypothesis

Visible concepts improve trust, deliberate composition, and attribute recovery.

### Failure signal

Users spend more time managing concepts than evaluating art, or confuse concept strength with image quality.

## 9. Interface C — Lane board

### Layout

- committed/preview hero image;
- three candidate columns: active composition, alternate learned lane, and discovery;
- active and inactive concept strips;
- advanced concept drawer.

For candidate delta \(\hat\delta\), classification is `active` when aligned with an effective concept, `alternate` when aligned with a learned but inactive concept, and `discovery` otherwise. Classification is descriptive. It does not alter the server's four proposal roles or posterior.

### Intended user model

> Every round offers continuation, remembered alternatives, and novelty.

### Primary hypothesis

Making exploration structure visible helps users understand the system and reduces accidental collapse into one aesthetic basin.

### Failure signal

Lane labels bias choices, candidates move unexpectedly after activation changes, or uneven column populations make comparison awkward.

## 10. Interaction invariants

Every experiment must preserve:

```text
preview is not commit
favorite is not commit
reroll keeps the anchor
underexposed reroll is a skip
New world is not dislike
history restore is exact and recoverable
stale SSE/HTTP snapshots cannot rewind state
failed candidates are not negative evidence
```

Touch long-hold preview suppresses the subsequent synthetic click. Preview exposure requires sustained inspection rather than pointer transit alone. Candidate favorite marks the candidate as meaningfully exposed before sending the favorite command.

## 11. Metrics

### Product outcome

- exports or durable favorites per session;
- choices to first durable favorite;
- branch depth;
- successful history recovery;
- session completion and return.

### Concept usefulness

- accepted deltas explained by existing lanes;
- number of lanes created per ten commits;
- lane reuse across seeds;
- lane reuse across prompts within one basis;
- composition-recast success rate;
- user-rated preservation of active lanes;
- forced on/off corrections per automatic decision;
- lane dormancy and deletion rates.

### Interaction burden

- explicit concept operations per session;
- time spent in concept controls;
- accidental activation changes;
- mobile error rate;
- comprehension of auto/on/off;
- subjective workload.

### Exploration quality

- action-space and perceptual diversity;
- distribution across active/alternate/discovery selections;
- repeated motif collapse;
- `none of these` frequency;
- user-rated surprise that remains useful.

## 12. Required studies

### Study A: attribute recovery

Participants discover A, move to a branch emphasizing B, then try to recover A+B under a new seed. Compare baseline, implicit lanes, and concept shelf.

### Study B: interaction burden

Open-ended 20-minute creation task. Compare explicit operations, workload, satisfaction, and outcome quality.

### Study C: system legibility

Ask participants to predict the effect of recast and lane activation. Compare implicit lanes, shelf, and lane board.

### Study D: lane validity

For every promoted lane, render controlled sweeps across seeds and prompts. Measure monotonicity, preservation, and cross-context consistency.

### Study E: automatic activation

Compare no automatic activation, threshold activation, hysteretic activation, and posterior-probability activation.

## 13. Promotion gates

Concept lanes should move into authoritative server state only when:

1. repeated accepted deltas produce stable lanes more often than accidental seed-specific clusters;
2. composition recasts preserve user-recognized attributes above a predefined success threshold;
3. users can understand and correct automatic activation;
4. lane growth remains bounded without constant cleanup;
5. at least one treatment improves attribute-recovery outcomes without unacceptable interaction cost.

Planner integration should occur only after server-side concepts exist. Then the proposal center can blend current realization and concept composition, and candidate roles can explicitly include composition-local, alternate-lane, and unexplained-discovery proposals.

## 14. Known limitations

- browser-local concepts do not follow the user to another device;
- action-delta clustering assumes the current codec coordinates are meaningful enough to compose;
- accepted deltas can reflect seed accidents and interactions rather than isolated attributes;
- lane names are placeholders;
- candidate classification is local and heuristic;
- the current server planner remains image-centered within ordinary rounds;
- the three layouts are research treatments, not polished final product recommendations.

## 15. Running the experiments

Run any UI directly:

```text
http://localhost:8000/ui/current-image
http://localhost:8000/ui/implicit-lanes
http://localhost:8000/ui/concept-shelf
http://localhost:8000/ui/lane-board
```

Or select the root UI:

```bash
ART_OPTIMIZER_UI=implicit-lanes python -m art_optimizer.app --host 0.0.0.0 --port 8000
```

The same saved session ID and concept library are reused when switching interfaces in one browser. This permits within-session comparison without changing the underlying generated state.
