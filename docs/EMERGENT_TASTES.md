# Emergent Tastes Runtime Treatment

**Status:** implemented experimental treatment  
**Route:** `/ui/emergent-tastes`  
**Treatment ID:** `emergent-tastes`

## Goal

Test whether coherent preference modes can emerge naturally from repeated votes while the
stochastic image root is fixed and candidate variance comes from the existing embedding/action
controls.

This treatment deliberately holds the T0 candidate planner constant. It changes the command
semantics, records self-contained fixed-root observations, and adds one replayable taste inference
projection. The taste projection does not yet steer candidate generation.

## Interaction contract

| Action | Navigation | Legacy planner evidence | Emergent-taste evidence |
|---|---|---:|---:|
| choose candidate | move to the rendered candidate | full candidate win | full candidate win |
| None fit | keep current image | weak anchor win | weak anchor win |
| New directions | keep current image; widen action radius | none | none |
| Resume from exemplar | restore an existing branch | restore historical branch state | none |

`New directions` calls the existing reroll transition with an empty exposure set. The world seed,
prompt, renderer, and control basis remain unchanged.

## Model

Each taste component has an ideal point \(\theta_k\) in the current action/control coordinates:

\[
u_k(a)=-\frac{\beta}{2}\lVert a-\theta_k\rVert^2.
\]

For one displayed slate, the component predicts the selected alternative with a softmax over the
anchor and meaningfully exposed candidates.

The runtime fits one-, two-, and three-component models. Components have a fixed persistence term,
so a coherent run of votes is more likely to remain in one taste than to switch on every click.
This is a small sticky hidden-state mixture rather than a manually managed taste shelf.

Before every vote, every candidate model emits a predictive probability. That receipt is stored in
the immutable `emergent_taste_choice_recorded` event before the vote is used for refitting. Model
selection uses cumulative chronological log score with a structural penalty and minimum evidence
mass. A second or third taste therefore appears only when it predicts later votes better than a
simpler model.

## Persistence and replay

Taste observations are self-contained session events containing:

- exact anchor and exposed alternatives;
- action vectors and rendered design IDs;
- fixed world seed and control-basis revision;
- winner and observation weight;
- result branch checkpoint;
- before-outcome predictive receipts.

The projection is rebuilt deterministically from these events after restart. Cached projections are
operational accelerators only.

## UI pattern

The right rail is a projection of discovered modes, not a mode-management form.

- Taste A/B/C appear automatically.
- Each mode shows evidence mass and recent representative winners.
- `Resume from exemplar` restores a real historical branch without adding another vote.
- The live scoreboard exposes whether one-, two-, or three-taste explanations are active, testing,
  or still under-supported.

The UI intentionally does not invent semantic attribute names. A taste is a preferred region, not a
claim that a causal visual attribute has been extracted.

## Explicit boundary

Implemented here:

- fixed-root embedding/action evidence;
- truthful neutral exploration versus anchor rejection;
- sticky ideal-point mixture;
- before-outcome receipts and chronological model selection;
- deterministic replay;
- automatic taste cards and exemplar resume UX.

Not implemented here:

- learned reusable embedding directions;
- visual-attribute extraction;
- image-embedding clustering;
- taste-authoritative candidate planning;
- parent-conditioned image evolution;
- cross-prompt or cross-control-basis transport.
