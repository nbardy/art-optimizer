# Art Optimizer

Art Optimizer is an open research platform for human-in-the-loop image search, image-evolution experiments, and persistent visual preference learning.

## Current status

Two materially different treatments are runnable.

### T0 Controlled Search

```text
prompt-conditioned control chart
    → four rendered alternatives
    → exposure-aware choice
    → branch-local preference update
    → exact history and replay
```

T0 is technically stable and remains the control baseline. Its current-image UI and three legacy concept-layout routes share one generation and learning policy.

### Emergent Tastes

```text
fixed seed + prompt + renderer
    → four embedding/action variations
    → predict vote before learning
    → sticky ideal-point mixture refit
    → expose only predictively supported taste modes
```

The isolated route `/ui/emergent-tastes` adds truthful `None fit` versus neutral `New directions`, self-contained vote events, deterministic replay, and automatic Taste A/B/C projections with representative branch exemplars. The T0 planner remains authoritative in this first ablation, so the new treatment tests the taste mathematics and UX without simultaneously changing candidate acquisition.

See [`docs/EMERGENT_TASTES.md`](docs/EMERGENT_TASTES.md) for its exact model, interaction contract, and non-claims.

Round 1 testing established that the project should **not** yet be described as:

- parent-conditioned image evolution;
- learned visual-attribute discovery;
- learned reusable embedding directions;
- or perceptually diverse candidate generation.

The renderer currently searches eight hand-authored prompt-embedding directions. Selecting a candidate promotes that rendered point and action; it does not pass the selected image back into FLUX as a generative parent. The legacy browser Concept Library stores accepted action movements rather than recurring visual patterns.

Start with:

- [`docs/EMERGENT_TASTES.md`](docs/EMERGENT_TASTES.md) — implemented fixed-root taste treatment;
- [`ROADMAP.md`](ROADMAP.md) — Round 2 sequence and promotion gates;
- [`docs/README.md`](docs/README.md) — documentation status and authority;
- [`reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md`](reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md) — Round 1 diagnosis;
- [`experiments/round2/README.md`](experiments/round2/README.md) — broader planned experiments.

## Repository map

```text
art_optimizer/      executable application
 tests/              unit, integration, and browser-contract tests
 scripts/            operational and benchmark scripts
 docs/               architecture and implementation contracts
 reviews/            prior work, design reviews, postmortems, raw source notes
 experiments/        executable hypotheses and result receipts
 ROADMAP.md           current research/product sequence
```

See [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) for the staged organization plan.

## What works today

- local procedural reference renderer;
- local FLUX.2 Klein and Krea 2 Turbo Diffusers stacks;
- model/codec selection without hosted generation APIs;
- BF16 inference and ordinary Hugging Face caching;
- streamed four-candidate browser interactions;
- fixed-seed candidate rendering within a world;
- exposure-aware multinomial choice updates;
- favorites, New world, exact history restoration, and branching in T0;
- sticky one-/two-/three-taste ideal-point inference in the emergent treatment;
- before-outcome predictive receipts and chronological model selection;
- deterministic taste replay from SQLite events;
- SQLite session persistence and render manifests;
- all four T0 presentation routes retained alongside the isolated emergent-tastes route.

## Quick start: CPU reference renderer

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make dev
```

Open the default T0 route:

```text
http://localhost:8000
```

Or open the emergent-tastes treatment directly:

```text
http://localhost:8000/ui/emergent-tastes
```

## Local open-weight models

Install the optional model stack:

```bash
pip install -e '.[dev,models]'
```

### FLUX.2 Klein 4B

```bash
ART_OPTIMIZER_MODEL=flux2-klein \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 127.0.0.1 --port 8000
```

### Krea 2 Turbo

```bash
ART_OPTIMIZER_MODEL=krea2-turbo \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 127.0.0.1 --port 8000
```

Hugging Face downloads missing files into its normal cache and reuses them on later runs. The application data directory stores session state, generated artifacts, and manifests—not duplicate model weights.

Useful options:

```bash
export HF_TOKEN=...                            # only if the model requires access
export HF_HOME=/path/with/more/disk           # optional cache location
export ART_OPTIMIZER_LOCAL_FILES_ONLY=1       # require cached/local files
export ART_OPTIMIZER_MODEL_REVISION=...       # pin a checkpoint revision
export ART_OPTIMIZER_CPU_OFFLOAD=1             # reduce VRAM at a latency cost
export ART_OPTIMIZER_CONDITIONING_MODE=prompt  # prompt-string baseline
```

## UI routes

```text
/ui/current-image       T0 baseline
/ui/implicit-lanes      T0 presentation variant
/ui/concept-shelf       T0 presentation variant
/ui/lane-board          T0 presentation variant
/ui/emergent-tastes     isolated fixed-root taste treatment
```

The first four routes share the T0 backend policy. `/ui/emergent-tastes` has different command semantics and a separate replayable taste projection, while deliberately holding the T0 candidate planner constant.

Choose the root route at startup:

```bash
ART_OPTIMIZER_UI=emergent-tastes python -m art_optimizer.app
```

## Remote access

Bind the server to loopback and use an SSH tunnel:

```bash
# GPU node
python -m art_optimizer.app --host 127.0.0.1 --port 8000

# laptop
ssh -L 8000:127.0.0.1:8000 user@node
```

Then open `http://localhost:8000`.

The development server does not provide authentication or TLS. Do not expose it directly to the public Internet; use an SSH tunnel, VPN, or authenticated HTTPS reverse proxy.

## Research direction

The clean near-term sequence is:

1. **Validate emergent tastes** — determine whether extra modes improve chronological vote prediction and are understandable in use.
2. **Embedding-direction ablation** — compare authored, random soft, prompt-manifold, and interaction-retained direction banks with the seed fixed.
3. **Taste-authoritative planning** — only after the shadow model wins, let the active mode steer candidate roles in a separate treatment.
4. **Reusable direction extraction** — promote recurring embedding transformations only after transfer tests across independent anchors.
5. **True image evolution** — separately add parent-conditioned rendering and preservation controls.

The baseline remains runnable throughout so each intervention has an honest comparison.

## Tests

```bash
python -m compileall -q art_optimizer tests scripts
python -m ruff check .
python -m pytest
for file in art_optimizer/static/*.js; do node --check "$file"; done
node tests/js/test_concept_library.mjs
node tests/js/test_emergent_tastes.mjs
```

With a server running:

```bash
python scripts/smoke_test.py http://localhost:8000
```

## API

T0:

```text
GET  /healthz
GET  /api/models
GET  /api/ui-experiments
POST /api/sessions
GET  /api/sessions/{session_id}
GET  /api/sessions/{session_id}/events
GET  /api/sessions/{session_id}/event-log
POST /api/sessions/{session_id}/candidates/{candidate_id}/commit
POST /api/sessions/{session_id}/reroll
POST /api/sessions/{session_id}/new-world
POST /api/sessions/{session_id}/designs/{design_id}/favorite
POST /api/sessions/{session_id}/history/{branch_node_id}/restore
```

Emergent tastes:

```text
POST /api/emergent-tastes/sessions
GET  /api/emergent-tastes/sessions/{session_id}
GET  /api/emergent-tastes/sessions/{session_id}/events
POST /api/emergent-tastes/sessions/{session_id}/candidates/{candidate_id}/commit
POST /api/emergent-tastes/sessions/{session_id}/none-of-these
POST /api/emergent-tastes/sessions/{session_id}/explore
POST /api/emergent-tastes/sessions/{session_id}/history/{branch_node_id}/restore
```

## Licenses

Art Optimizer code is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, references, and generated-media obligations retain their own licenses. FLUX.2 Klein 4B is Apache-2.0. Krea 2 uses the Krea 2 Community License rather than an OSI-approved open-source license; review its commercial and deployment terms before use.
