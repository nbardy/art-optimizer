# Art Optimizer

**Art Optimizer** is an open-source, human-in-the-loop interface for exploring generative image spaces without requiring users to describe every visual preference in words.

The primary interaction is deliberately small:

1. one design fills the canvas;
2. four candidate descendants sit in the corners;
3. hovering previews a candidate at full size;
4. clicking commits it as the current design;
5. rerolling means “none of these—keep searching from here”;
6. starring preserves a design as durable preference evidence;
7. **New world** changes the stochastic root without forgetting the user’s broader taste.

The product treats the current design as an immutable, replayable generative state—not merely a PNG. Every committed choice retains the model revision, conditioning, materialized initial noise, control vector, parent, and proposal policy needed to reproduce and branch from it.

## Status

This repository currently contains the initial product and technical design. It is **pre-implementation**: the interfaces and algorithms are proposals to be tested, not claims of completed model performance.

## Design thesis

Art Optimizer combines three ideas:

- **Local interactive design search:** learn what the user wants in the current branch from a small number of comparative choices.
- **Persistent generative recommendation:** learn durable, possibly multi-modal taste from stars, revisits, exports, and prior sessions.
- **Controllable generation:** search a compact action manifold spanning conditioning, references, adapters, attention interventions, and bounded directions in initial-noise space.

The first implementation should use a **contextual preferential bandit / preferential Bayesian optimizer**, not full long-horizon reinforcement learning. Four-way choices are modeled as discrete-choice observations, while reroll is an explicit outside option.

## Proposed model substrate

As of **2026-08-19**, the default research target is [FLUX.2 \[klein\] 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B): a four-step, Apache-2.0, open-weight model supporting text-to-image, image editing, and multi-reference generation. The architecture keeps the renderer behind an adapter so Krea 2 Turbo, SANA-Sprint, and later checkpoints can be benchmarked without rewriting the product or optimizer.

## Documentation

- [UI design](docs/UI_DESIGN.md) — the single-image canvas, corner previews, history, favorites, reset, responsive behavior, and event semantics.
- [Research notes](docs/RESEARCH_NOTES.md) — Ryan Murdock, Evan Shimizu, related work, mathematical formulation, model survey, and open research questions.
- [Architecture](docs/ARCHITECTURE.md) — system boundaries, services, storage, event flow, determinism, deployment, safety, and observability.
- [Code design](docs/CODE_DESIGN.md) — repository layout, domain types, state machines, APIs, optimizer and renderer interfaces, noise subspaces, and testing.
- [Contributing](CONTRIBUTING.md) — how to propose research, interface, and implementation changes.

## Core invariants

1. **Preview is not commitment.** Hover or press-and-hold may change the displayed image, but only an explicit selection advances the branch.
2. **A current design is complete state.** The rendered image is an output; exact generator state and provenance are authoritative.
3. **Reroll preserves the branch root.** It is weak “none of these” evidence, not a destructive reset.
4. **New world is not a downvote.** It changes the initial-noise root while retaining persistent taste.
5. **Integer seed adjacency has no meaning.** Search occurs in materialized noise tensors or a defined continuous subspace, never by adding numbers to a PRNG seed.
6. **The four candidates must have roles.** A slate should balance predicted preference, uncertainty, diversity, and controlled surprise rather than showing four near-duplicates.
7. **Historical choices remain replayable.** The visible last-ten strip is a view over an underlying branch tree, not the complete record.
8. **The model adapter is replaceable.** Model-specific controls do not leak into product-level session semantics.

## Initial implementation slice

The first end-to-end slice should support:

- one text prompt and optional reference images;
- one persistent GPU renderer;
- one fixed materialized root-noise tensor per world;
- a 16–32 dimensional bounded control manifold;
- four streamed candidate descendants per round;
- hover preview and click/tap commit;
- reroll, star, new world, and restore/fork from the last ten committed designs;
- an event-sourced session record;
- a Bayesian linear or pairwise-GP preference model;
- uncertainty- and diversity-aware slate construction;
- exact deterministic replay tests.

See [CODE_DESIGN.md](docs/CODE_DESIGN.md) for the executable interfaces and [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the deployment path.

## License

The repository is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, and third-party dependencies retain their own licenses; the renderer must record and enforce the license attached to each configured model.
