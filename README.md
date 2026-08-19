# Art Optimizer

**Art Optimizer** is an open-source, human-in-the-loop interface for exploring generative image spaces without requiring users to describe every visual preference in words.

The primary interaction is deliberately small:

1. one design fills the canvas;
2. four candidate descendants sit in the corners;
3. hovering or holding previews a candidate at full size;
4. clicking or tapping commits it as the current design;
5. rerolling means “the current design beats these alternatives—keep searching from here”;
6. starring preserves a design as durable preference evidence;
7. **New world** changes the stochastic root without forgetting the user’s broader taste.

The product treats the current design as an immutable, replayable generative state—not merely a PNG. Every committed choice retains the model revision, conditioning, materialized initial noise, absolute world-level control coordinates, parent, learner snapshot, and proposal policy needed to reproduce and branch from it.

## Status

The v0 product and algorithm design is **implementation-ready**. The interaction semantics, local choice model, persistent preference atlas, and implementation gates are now normative rather than a menu of alternatives.

The repository remains **pre-code**. In particular, no real image model has yet passed the required replay, latency, and useful-control-basis experiments. “Implementation-ready” means engineers can build and test the system without inventing semantics; it does not claim that personalized image optimization quality has already been demonstrated.

See [Implementation readiness](docs/IMPLEMENTATION_READINESS.md) for the exact verdict, empirical gates, risk register, and pull-request sequence.

## Design thesis

Art Optimizer combines three ideas:

- **Local interactive design search:** learn what the user wants in the current branch from a small number of comparative choices.
- **Persistent generative recommendation:** maintain and evolve a multimodal atlas of durable taste from favorites, exports, revisits, and weak selection evidence.
- **Controllable generation:** search a compact, bounded action manifold spanning conditioning, references, adapters, attention interventions, and—after validation—world-local directions in initial-noise space.

The first implementation uses a **contextual preferential bandit / sequential Bayesian optimizer**, not full long-horizon reinforcement learning. A round is one multinomial choice among the current anchor and meaningfully exposed candidates. Reroll selects the anchor as a weak outside-option observation.

Persistent taste is not one average user embedding. It is an evolving bank of coherent components that can go dormant, reactivate, guide new-world proposals, and reserve explicit probability for exploration outside known taste.

## Normative v0 specifications

Use this precedence when documents differ:

1. [Interaction model v0](docs/INTERACTION_MODEL_V0.md) — exact preview, commit, favorite, reroll, New-world, exposure, and history semantics.
2. [V0 algorithm specification](docs/V0_ALGORITHM_SPEC.md) — absolute world controls, choice likelihood, Laplace posterior, trust region, candidate roles, and noise policy.
3. [Persistent preference atlas](docs/PERSISTENT_PREFERENCE_ATLAS.md) — evolving multimodal preference components, evidence, lifecycle, and generation guidance.
4. [Implementation readiness](docs/IMPLEMENTATION_READINESS.md) — locked decisions, remaining empirical gates, contract deltas, and implementation sequence.

## Proposed model substrate

As of **2026-08-19**, the default research target is [FLUX.2 \[klein\] 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B): a four-step, Apache-2.0, open-weight model supporting text-to-image, image editing, and multi-reference generation. The architecture keeps the renderer behind an adapter so Krea 2 Turbo, SANA-Sprint, and later checkpoints can be benchmarked without rewriting the product or optimizer.

The model choice is provisional. A real adapter must pass the replay, useful-control-basis, and latency gates before becoming the supported v0 renderer.

## Supporting documentation

- [UI design](docs/UI_DESIGN.md) — visual layout, responsive behavior, accessibility, loading, and interaction rationale.
- [Research notes](docs/RESEARCH_NOTES.md) — Ryan Murdock, Evan Shimizu, related work, model survey, and research questions.
- [Architecture](docs/ARCHITECTURE.md) — system boundaries, services, storage, event flow, determinism, deployment, safety, and observability.
- [Code design](docs/CODE_DESIGN.md) — repository layout, domain types, APIs, renderer interfaces, persistence, tests, and earlier implementation sketches.
- [Contributing](CONTRIBUTING.md) — how to propose research, interface, and implementation changes.

## Core invariants

1. **Preview is not commitment.** Hover or press-and-hold may change displayed pixels, but only an explicit selection advances the branch.
2. **A current design is complete state.** The rendered image is an output; exact generator state and provenance are authoritative.
3. **The anchor is the outside option.** Commit chooses a candidate over the current design; reroll chooses the current design over exposed candidates.
4. **Reroll preserves the branch root.** It is weak local evidence, not a destructive reset or durable taste update.
5. **New world is not a downvote.** It changes the initial-noise root while retaining the persistent preference atlas.
6. **Integer seed adjacency has no meaning.** Search occurs in materialized noise geometry or a defined continuous subspace, never by adding numbers to a PRNG seed.
7. **Persistent taste is multimodal.** Strong novel evidence may spawn a component; weak exploratory clicks may not.
8. **The four candidates have distinct roles.** Exploitation, diverse posterior sampling, uncertainty probing, and persistent-mode/controlled surprise prevent top-four collapse.
9. **Historical choices remain replayable.** The visible last-ten strip is a view over an immutable branch forest.
10. **The model adapter is replaceable.** Model-specific controls do not leak into product-level session semantics.
11. **Raw events remain facts.** Learner weighting and preference projections are rebuildable, versioned interpretations.
12. **No real renderer is accepted without receipts.** Replay, control smoothness, latency, hardware, and model digests are measured rather than assumed.

## Locked v0 algorithm

The first optimizer uses:

- one bounded absolute action vector per world, with at most 16 dimensions;
- fixed materialized root noise while the first semantic/control basis is validated;
- a quadratic feature map over action coordinates;
- a Bayesian linear utility model with a Laplace posterior;
- one multinomial observation over the anchor and exposed candidates;
- a finite Sobol/Gaussian proposal pool;
- a branch trust region;
- four role-specific candidates;
- an evolving persistent preference atlas used as a proposal/guidance source;
- no long-horizon RL and no per-click generator fine-tuning.

Optional tangent-space noise coordinates are feature-gated until they pass their own replay and usefulness tests.

## Clean implementation sequence

1. **Contracts and fake renderer:** versioned schemas, pure reducers, SQLite events, semantic hashing, CI.
2. **Interaction shell:** one canvas, four corners, preview, commit, current/candidate favorites, reroll/skip, New world, history.
3. **Real renderer spike:** one adapter, root noise, absolute controls, capability refusal, replay and latency receipts.
4. **Local optimizer:** choice likelihood, Laplace update, trust region, four proposal roles, simulated-user baselines.
5. **Persistent preference atlas:** evidence ledger, multimodal components, exemplar guidance, privacy/export/deletion.
6. **Integrated research release:** reproducible local setup, benchmark receipts, sample sessions, and documented failure modes.

The real model is intentionally not the first code pull request. The product state machine should be executable and fully tested with a deterministic fake renderer before GPU integration.

## License

The repository is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, and third-party dependencies retain their own licenses; the renderer must record and enforce the license attached to each configured model.
