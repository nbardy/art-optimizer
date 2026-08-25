# Track CQ-3 — Frontend Duplication and Shared Modules

## Executive finding

The browser code is the clearest 2× reduction opportunity in the repository. The current-image UI, emergent-taste UI, concept experiment controller, and taste gallery each implement overlapping application infrastructure. The duplication is not cosmetic: fixes to exposure, conflict recovery, error formatting, accessibility, and SSE behavior can land in one UI but not another.

The right target is a **headless session client plus small view adapters**, not a single giant universal UI component.

## 1. Repeated application shell

Compare:

- [`static/app.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/app.js)
- [`static/emergent_tastes.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/emergent_tastes.js)
- [`static/experiment_core.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/experiment_core.js)
- [`static/taste_gallery.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/taste_gallery.js)

Repeated mechanisms include:

```text
request ID generation
JSON API wrapper
error parsing
busy/disabled state
session persistence in localStorage
resume behavior
SSE connection and reconnection
conflict refresh
active-round identity
meaningful-exposure tracking
candidate lookup and card updates
image URL normalization
preview lifecycle
history rendering and restore
keyboard controls
toasts
```

`experiment_core.js` was intended to provide some sharing, but `app.js` and `emergent_tastes.js` still own parallel controllers.

## 2. Semantic divergence caused by duplication

### Error formatting

The experimental clients import `formatRequestError`; the baseline `app.js` still uses:

```javascript
new Error(body.detail || `Request failed (${response.status})`)
```

so structured FastAPI validation errors render differently.

### Resume behavior

Both principal UIs catch every resume error and remove the local session ID. This silently converts a network outage or server bug into “your session is gone.” A shared session client could distinguish 404 from retryable failure.

### Exposure behavior

Exposure tracking has evolved in several places. Any threshold or stale-round fix must be audited across multiple controllers.

### Candidate role labels

The baseline and emergent UI use different labels for the same planner roles. Because roles are fixed to slots and visible to users, this is not only wording duplication; it is an experimental confound.

## 3. Taste gallery is attached by DOM surgery

[`taste_gallery.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/taste_gallery.js) watches `#taste-list` with a `MutationObserver`, parses visible titles like `Taste A`, reconstructs `taste-1`, and appends buttons after the emergent UI renders cards.

```javascript
const title = card.querySelector(".taste-card-title")?.textContent || "";
const tasteId = tasteIdFromLabel(title);
```

This is a brittle integration boundary:

- changing the label format breaks identity;
- localization breaks identity;
- a display reorder can change the inferred ID;
- the gallery module cannot receive typed component data directly;
- event listeners are managed through DOM flags.

The emergent view should render a taste-card component with explicit data:

```javascript
renderTasteCard({ tasteId, label, exemplars, onBrowse, onResume })
```

No label parsing or mutation observer is necessary.

## 4. Gallery UX has an avoidable blocking state

The gallery uses one synchronous request to render up to 42 images. While it is busy:

```javascript
function closeOverlay() {
  if (state.busy) return;
  ...
}
```

The user cannot dismiss the modal during a potentially long real-model render. There is no cancellation or partial-cell progress because the API returns only after `asyncio.gather` completes.

A clean pattern is:

```text
POST create manifest/job
GET/SSE stream per-cell states
DELETE cancel gallery job
```

The modal can close at any time; the job may continue or cancel by explicit policy.

## 5. Recommended module split

### `session_client.js`

Own:

- request IDs;
- typed API calls;
- command envelopes;
- 404/conflict/retry classification;
- SSE connection and reconnection;
- session persistence;
- snapshot version monotonicity.

### `candidate_exposure.js`

Own:

- intersection/hold exposure qualification;
- active-round reset;
- ready-only exposure extraction;
- cleanup.

### `candidate_grid.js`

Own:

- card DOM;
- preview events;
- keyboard and touch behavior;
- loading/failed states;
- no treatment-specific role labels unless debug policy enables them.

### `history_view.js`

Own reusable checkpoint rendering and restore callbacks.

### Treatment adapters

```javascript
createControlledSearchView(client, nodes, policy)
createEmergentTasteView(client, nodes, tasteProjection)
createConceptLegacyView(client, nodes, conceptLibrary)
```

The adapters should provide command vocabulary and additional panels, not rebuild transport and exposure machinery.

### Gallery component

The gallery should be a normal child view receiving explicit `TasteComponent` data. It should not read localStorage independently or infer identity from rendered text.

## 6. Reduction estimate

The repeated client/controller behavior spans well over a thousand lines across `app.js`, `emergent_tastes.js`, `experiment_core.js`, and `taste_gallery.js`.

A realistic target:

```text
shared client/exposure/candidate/history modules: 450–650 lines
baseline adapter:                           150–220 lines
emergent adapter + taste rail:              250–350 lines
gallery component:                          180–250 lines
legacy concept adapters:                    250–400 lines
```

This can remove approximately 40–55% of frontend controller code while making behavior more consistent.

## 7. What not to share

Do not force these into generic switches:

- emergent taste model scoreboard;
- browser concept controls;
- baseline favorite/new-world vocabulary;
- gallery seed-strength grid;
- treatment-specific explanatory copy.

Share infrastructure and typed state, not every visual layout.

## Verdict

**Frontend slop:** high duplication, moderate local readability.  
**Bug risk:** fixes can diverge between treatments.  
**Reduction potential:** approximately 2× in controllers without sacrificing experiments.  
**First action:** create `session_client.js` and `candidate_exposure.js`, then migrate baseline and emergent UIs before touching visual design.
