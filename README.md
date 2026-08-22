# Art Optimizer

Art Optimizer is an open research platform for human-in-the-loop image search, image-evolution experiments, and persistent visual preference learning.

## Current status

The current runnable treatment is **T0 Controlled Search**:

```text
prompt-conditioned control chart
    → four rendered alternatives
    → exposure-aware choice
    → branch-local preference update
    → exact history and replay
```

It is technically stable and useful as a baseline. Round 1 testing showed that it should **not** yet be described as:

- parent-conditioned image evolution;
- learned visual-concept discovery;
- perceptually diverse candidate generation;
- or several independent algorithm/UI experiments.

The current implementation searches eight hand-authored prompt-embedding directions. Selecting a candidate promotes that rendered point and action; it does not pass the selected image back into FLUX as a generative parent. The browser concept shelf stores accepted action movements rather than recurring visual patterns.

Start with:

- [`ROADMAP.md`](ROADMAP.md) — Round 2 sequence and promotion gates;
- [`docs/README.md`](docs/README.md) — documentation status and authority;
- [`reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md`](reviews/11_ROUND_1_ROOT_CAUSE_REVIEW.md) — Round 1 diagnosis;
- [`experiments/round2/README.md`](experiments/round2/README.md) — planned treatments.

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
- browser UI with streamed candidates;
- exposure-aware multinomial choice updates;
- favorites, New world, exact history restoration, and branching;
- SQLite persistence and render manifests;
- original and concept-layout UI routes retained as T0 presentation variants.

## Quick start: CPU reference renderer

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make dev
```

Open:

```text
http://localhost:8000
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
export HF_TOKEN=...                         # only if the model requires access
export HF_HOME=/path/with/more/disk        # optional cache location
export ART_OPTIMIZER_LOCAL_FILES_ONLY=1    # require cached/local files
export ART_OPTIMIZER_MODEL_REVISION=...    # pin a checkpoint revision
export ART_OPTIMIZER_CPU_OFFLOAD=1          # reduce VRAM at a latency cost
export ART_OPTIMIZER_CONDITIONING_MODE=prompt  # prompt-string baseline
```

## UI routes

The original UI remains available alongside the Round 1 concept-layout variants:

```text
/ui/current-image
/ui/implicit-lanes
/ui/concept-shelf
/ui/lane-board
```

These currently share the same backend policy and should be treated as **presentation variants**, not independent optimization treatments. Round 2 will define complete policy bundles before calling interfaces separate experiments.

Choose the root route at startup:

```bash
ART_OPTIMIZER_UI=current-image python -m art_optimizer.app
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

Round 2 separates four lines of work:

1. **Truthful controlled search** — split neutral novelty from negative preference and measure diversity on outputs.
2. **Random soft-direction search** — explore calibrated conditioning directions that may be difficult to express as strings.
3. **True image evolution** — add parent-conditioned rendering and preservation constraints.
4. **Provisional visual concepts** — require recurring visual evidence before a learned object becomes composable.

The current baseline remains runnable throughout so each intervention has an honest comparison.

## Tests

```bash
python -m compileall -q art_optimizer tests scripts
python -m ruff check .
python -m pytest
node --check art_optimizer/static/app.js
node --test tests/js/test_concept_library.mjs
```

With a server running:

```bash
python scripts/smoke_test.py http://localhost:8000
```

## API

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

## Licenses

Art Optimizer code is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, references, and generated-media obligations retain their own licenses. FLUX.2 Klein 4B is Apache-2.0. Krea 2 uses the Krea 2 Community License rather than an OSI-approved open-source license; review its commercial and deployment terms before use.
