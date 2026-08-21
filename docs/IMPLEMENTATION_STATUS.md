# Implementation Status

**Status:** runnable v0.3 research implementation  
**Last updated:** 2026-08-21

## Complete interaction and learning loop

The repository executes the complete browser-to-renderer loop:

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

The CPU procedural renderer remains the deterministic reference used by ordinary tests and UI development.

## Local real-model stacks

Two local/open-weight targets are implemented behind the same model profile, semantic codec, renderer, persistence, and UI contracts:

- `flux2-klein` — `black-forest-labs/FLUX.2-klein-4B` through `Flux2KleinPipeline`;
- `krea2-turbo` — `krea/Krea-2-Turbo` through `Krea2Pipeline`.

No hosted generation API is used. Model dependencies are optional and weights load lazily. The selected model is fixed for one server process so only one large checkpoint occupies GPU memory.

## Embedding-level controls

The default real-model codec operates directly on the model text-embedding surface. For each fixed world prompt it encodes one batched set containing the base prompt and positive/negative endpoints for eight semantic axes, builds RMS-normalized directions, and mixes them by the optimizer's canonical action vector.

FLUX and Krea differ only in small conditioning adapters:

- FLUX consumes `prompt_embeds`;
- Krea consumes `prompt_embeds` plus `prompt_embeds_mask`.

`ART_OPTIMIZER_CONDITIONING_MODE=prompt` preserves an ordinary prompt-compilation baseline for controlled comparisons.

## Renderer and replay hardening

- explicit pipeline classes rather than generic pipeline guessing;
- one data-driven model registry with license and deployment metadata;
- fail-fast local-model dependency checks;
- optional model revision pinning;
- atomic image and manifest writes;
- cached images reused only when the complete render-request digest matches;
- model-specific runtime directories prevent cross-model session or artifact repair;
- active model, codec, conditioning mode, basis, replay level, and license reported by `/healthz`;
- full catalog reported by `/api/models`.

## Modular experiment boundaries

- renderer/model selection is composed in `composition.py`;
- model semantics and licenses live in `model_codec.py`;
- tensor-signature differences live in `embedding_conditioning.py`;
- acquisition lives in `planner.py`;
- local preference learning lives in `preference.py`;
- persistent memory lives in `atlas.py`;
- alternate browser builds can be selected with `ART_OPTIMIZER_STATIC_DIR` and use the same HTTP/SSE API.

The preference learner is isolated but still selected concretely by the current service. A future learner registry is a small composition-root extension, not a cross-cutting model or UI rewrite.

## Validation completed without model weights

The normal test path remains GPU-free. It covers the procedural renderer, service state machine, optimizer, atlas, persistence, API, UI syntax, and fake-pipeline tests for both FLUX and Krea codecs. The fake-pipeline tests verify batched endpoint encoding, Krea masks, embedding application, model metadata, and cache invalidation.

## Empirical gates still open

The code path is ready to run on a GPU node, but the real checkpoints were not downloaded or benchmarked in the implementation environment. Before either becomes the default, run:

- a real root and four-candidate smoke session;
- coordinate sweeps for all eight dimensions;
- cross-seed and cross-prompt smoothness tests;
- within-slate diversity and preservation measurements;
- VRAM and batch-of-four latency receipts;
- human comparison against prompt-only and random baselines;
- Krea deployment-license and content-filter review.

## Deferred product infrastructure

- authentication, TLS, and multi-user isolation;
- reference-image upload and atlas exemplar conditioning;
- export/provenance bundles;
- production GPU scheduling and object storage;
- collaborative preference learning;
- learned attention or adapter directions;
- offline LoRA/DPO consolidation.
