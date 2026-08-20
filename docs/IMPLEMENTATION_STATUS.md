# Implementation Status

**Status:** Runnable v0 reference implementation  
**Last updated:** 2026-08-20

## Implemented

The repository now executes the complete interaction and learning loop on a CPU:

```text
create world
→ render committed root
→ plan four role-balanced descendants
→ stream each candidate independently
→ preview without mutating state
→ commit one candidate or reroll to the anchor
→ update the branch-local posterior
→ favorite into persistent taste memory
→ start a new world without forgetting taste
→ restore and fork from recent branch checkpoints
```

The implementation lives in `art_optimizer/` and uses FastAPI, SQLite, NumPy, SciPy, Pillow, and framework-free browser JavaScript.

## Honest renderer boundary

`ProceduralRenderer` is the supported development renderer. It has:

- one fixed stochastic seed per world;
- a declared global eight-dimensional absolute control basis;
- deterministic replay from prompt, seed, and action;
- enough smooth variation to test preference learning and candidate planning;
- CPU rendering with no model download or API key.

It is not evidence that a diffusion checkpoint exposes equally useful coordinates. A real-model adapter remains blocked on `CONTROL_BASIS_EXPERIMENT.md`.

## Local preference learner

The implementation follows `V0_ALGORITHM_SPEC.md`:

- quadratic features over absolute action coordinates;
- Bayesian linear utility;
- one multinomial observation over anchor plus exposed candidates;
- reroll as anchor selection with weight `0.35`;
- damped Newton/Laplace posterior updates;
- slight covariance inflation to follow changing branch intent;
- posterior mean and variance used by acquisition.

## Candidate planner

The finite hidden pool combines:

- local Gaussian trust-region proposals;
- scrambled Sobol global coverage;
- declared atlas-guided proposals.

The displayed quartet has fixed policy roles:

1. best local continuation;
2. diverse posterior sample;
3. informative probe;
4. controlled surprise or alternate persistent mode.

## Persistent preference atlas

The atlas projection is persisted separately from session-local state.

- commits: weight `0.05`;
- revisits: weight `0.25`;
- favorites: weight `1.00`;
- exports: reserved weight `1.50`;
- strong novel events may spawn components;
- one weak novel event remains provisional;
- three coherent weak events from distinct designs may promote a component;
- unfavorite retracts the corresponding strong evidence and rebuilds the projection;
- outside-prior probability remains `0.20`.

The procedural renderer's action basis is globally stable, so component action centroids may bias new worlds. A diffusion adapter must use a declared validated transport, such as fixed exemplar/reference coordinates, instead of assuming action transfer.

## Streaming and persistence

- Each candidate renders in an independent asynchronous task.
- SSE publishes a fresh public session projection as slots progress.
- Images are durable before a candidate becomes selectable.
- Round IDs prevent stale results from mutating a newer round.
- Events and the matching session projection are written in one SQLite transaction.
- Ready sessions survive process restarts.
- Interrupted candidate rounds resume their unfinished slots when loaded.

## Interaction details implemented

- desktop hover preview;
- touch press-and-hold preview and tap commit;
- candidate-specific favorite without navigation;
- committed-image favorite that never retargets during preview;
- client-side 300 ms / 50% exposure qualification;
- reroll versus non-preference-bearing round skip;
- keyboard shortcuts `1`–`4`, `R`, `F`, `N`, and `H`;
- last-ten branch history and exact checkpoint restore;
- responsive layout and reduced-motion support.

## Validation completed

The test suite covers:

- deterministic renderer replay;
- four distinct candidate roles and bounded actions;
- selection learning and reroll behavior;
- posterior snapshot restoration;
- strong component spawning and weak-evidence promotion;
- favorite retraction;
- session creation, SSE initial delivery, candidate streaming, commit, favorite, reroll, New world, history restore, event logging, and restart persistence;
- API health and static application serving;
- JavaScript syntax validation.

A live server smoke test has also exercised HTTP creation, independently completed images, SSE delivery, posterior-dependent next-round scores, and static asset retrieval.

## Deliberately deferred

- real diffusion/flow model adapter;
- reference-image upload UI;
- authentication and multi-user isolation;
- export endpoint and downloadable provenance bundle;
- collaborative filtering across users;
- learned attention/adapter directions;
- offline LoRA or DPO consolidation;
- full event-log reducer migrations;
- production job broker/object store deployment.

These are extensions of the current contracts, not requirements for the executable local vertical slice.
