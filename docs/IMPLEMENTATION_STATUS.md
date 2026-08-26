# Implementation Status

**Status:** runnable v0.6 research implementation  
**Last updated:** 2026-08-26

## Runnable experiments

One server exposes six stable interfaces from the root experiment catalog:

```text
/ui/current-image
/ui/implicit-lanes
/ui/concept-shelf
/ui/lane-board
/ui/emergent-tastes
/ui/direction-lab
```

The first four are presentation variants over the original authored-axis T0 search. `emergent-tastes` adds replayable latent action-preference modes and read-only taste galleries. `direction-lab` is a separate generator-facing experiment over direct non-string prompt-embedding points.

## Original authored-axis loop

The repository executes the browser-to-renderer loop:

```text
create fixed-root world
→ render committed root
→ plan four authored-action candidates
→ stream candidates
→ preview without mutation
→ choose or reject
→ update branch-local posterior
→ persist exact branch checkpoints and choice facts
→ restore and fork
```

The CPU procedural renderer remains the deterministic reference used by ordinary tests and UI development.

## Direct random embedding points

Direction Lab bypasses the eight positive/negative prompt-axis strings. It encodes only the base prompt and adds direct embedding-tensor offsets measured in units of base-prompt RMS.

Four implementations are selectable:

- independent full-tensor Gaussian shell;
- exactly orthogonal full-tensor shell;
- structured rank-4 token-by-channel shell;
- antipodal `+u,-u,+v,-v` shell.

Every four-image slate shares one diffusion seed. Every direction is normalized to exact unit RMS, so shell radius directly specifies conditioning displacement. Selecting a candidate appends its exact deterministic step and makes that embedding point the next center. The API returns pre-render geometry receipts including pairwise RMS spacing, direction cosines, and effective rank.

See [`RANDOM_EMBEDDING_CODECS.md`](RANDOM_EMBEDDING_CODECS.md).

## Local real-model stacks

Two local/open-weight targets are implemented:

- `flux2-klein` — `black-forest-labs/FLUX.2-klein-4B` through `Flux2KleinPipeline`;
- `krea2-turbo` — `krea/Krea-2-Turbo` through `Krea2Pipeline`.

No hosted generation API is used. Model dependencies are optional and weights load lazily. The selected model is fixed for one server process so only one large checkpoint occupies GPU memory.

FLUX consumes `prompt_embeds`; Krea consumes `prompt_embeds` and its mask. `ART_OPTIMIZER_CONDITIONING_MODE=prompt` remains an authored prompt-compilation baseline, but Direction Lab intentionally refuses to run outside embedding mode.

## Correctness and replay hardening

Implemented runtime guarantees include:

- request-id idempotency and payload conflict checks;
- restorable same-design checkpoints after preference-bearing rejection;
- pending/final recovery for emergent choice facts;
- complete model/prompt/seed/basis scopes for learned observations;
- consistent weak-evidence likelihood semantics;
- convergence-gated finite sticky ideal-point modes;
- atomic image and manifest writes;
- complete render-request cache digests;
- bounded taste-gallery concurrency and partial-failure cleanup;
- serialized Direction Lab GPU slates;
- deterministic point and image seeds;
- model-specific runtime directories.

## Modular boundaries

- model profiles and authored endpoint prompts: `model_codec.py`;
- base prompt and conditioning tensor operations: `embedding_conditioning.py`;
- direct shell geometry and replayable embedding walks: `random_embedding_codec.py`;
- random slate API orchestration: `direction_lab.py`;
- Diffusers execution and artifact caching: `diffusers_renderer.py`;
- authored acquisition: `planner.py`;
- preference inference: `preference.py`, `taste_math.py`, and related typed modules;
- persistent memory: `atlas.py`;
- state machine and persistence: `service.py` and `event_store.py`.

## GPU-free validation

The local verification path covers:

- procedural renderer and service state machine;
- persistence and command recovery;
- authored optimizer and atlas;
- emergent-taste mathematics;
- taste galleries;
- all UI routes and browser helper contracts;
- deterministic shell geometry for all four random codecs;
- exact orthogonal and antipodal invariants;
- low-rank matrix rank;
- fake-pipeline fixed-seed direct-embedding rendering and cache reuse.

## Empirical gates still open

The implementation can control requested embedding variance exactly, but real FLUX/Krea image response remains empirical. The immediate test matrix is:

- four random codecs;
- matched radii from `0.10` to `0.80` base RMS;
- several prompts and point seeds;
- fixed diffusion seed within each comparison;
- usefulness, breakage, common-mode collapse, and subject-preservation judgments;
- latency and VRAM receipts.

Do not promote a codec because it merely produces larger changes. It must produce useful decisions at a tolerable broken/off-manifold rate.

## Deferred research and production work

- preference learning over a winning random basis;
- held-out reusable-direction extraction;
- parent-conditioned image evolution;
- authentication, TLS, and multi-user isolation;
- production GPU scheduling and object storage;
- export/provenance bundles;
- Krea deployment-license and content-filter review.
