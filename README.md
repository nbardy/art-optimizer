# Art Optimizer

Art Optimizer is an open research platform for human-in-the-loop image search,
embedding-space experiments, and persistent visual-preference learning.

## Experiment launcher

The bundled root route is always an experiment catalog:

```text
http://localhost:8000/
```

Every interface remains available at a stable route:

```text
/ui/current-image       T0 controlled-search baseline
/ui/implicit-lanes      T0 presentation variant
/ui/concept-shelf       T0 presentation variant
/ui/lane-board          T0 presentation variant
/ui/emergent-tastes     fixed-root emergent-taste treatment
```

There is no process-level UI selector. `ART_OPTIMIZER_UI` is not read. Experiment
identity belongs in the route, so one running server exposes every treatment.

`ART_OPTIMIZER_STATIC_DIR` remains available for deployment-specific custom static
applications. A custom directory supplies its own root `index.html` and does not
expose the bundled experiment routes.

## T0 controlled search

```text
prompt-conditioned control chart
    → four rendered alternatives
    → exposure-aware choice
    → branch-local preference update
    → exact history restoration
```

The first four routes share this generation and learning policy.

## Emergent tastes

```text
fixed seed + prompt + renderer
    → four embedding/action variations
    → predict the vote before training
    → sticky ideal-point mixture refit
    → expose only predictively supported taste modes
```

The `/ui/emergent-tastes` treatment adds truthful `None fit` versus neutral
`New directions`, replayable taste projections, and representative exemplars. The
T0 learner still chooses candidates in this first ablation.

### Taste galleries

Click any exposed taste to render a gallery where:

```text
vertical axis     different deterministic seeds
horizontal axis   different scalar strengths of the selected taste
```

For taste center \(\theta_k\) and strength \(s\):

\[
a(s,k)=\operatorname{clip}(s\theta_k,-1,1).
\]

Gallery rendering, previewing, and cell selection create no preference votes.
Selecting **Continue as new fixed-root session** starts a fresh session at the
cell's exact seed and action with an empty emergent-taste evidence stream.

See [`docs/TASTE_GALLERIES.md`](docs/TASTE_GALLERIES.md).

## Honest boundary

The renderer currently searches eight authored controls. The emergent engine learns
preferred regions over those coordinates; it does not discover or name reusable
visual attributes. It is not yet parent-conditioned image evolution or cross-prompt
taste transport.

The emergent projection also remains non-authoritative, and the base session mutation
and taste-event append are not yet one SQLite transaction.

## Quick start

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make dev
```

Open `http://localhost:8000/` and choose an experiment.

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

## Tests

```bash
python -m ruff check .
python -m compileall -q art_optimizer tests scripts
python -m pytest
for file in art_optimizer/static/*.js; do node --check "$file"; done
node tests/js/test_concept_library.mjs
node tests/js/test_emergent_tastes.mjs
node tests/js/test_taste_gallery.mjs
```

With a server running:

```bash
python scripts/smoke_test.py http://localhost:8000
```

## API

Core and catalog:

```text
GET  /
GET  /healthz
GET  /api/models
GET  /api/ui-experiments
GET  /ui/{experiment_id}
```

Emergent taste galleries:

```text
POST /api/emergent-tastes/sessions/{session_id}/tastes/{taste_id}/gallery
GET  /api/emergent-tastes/sessions/{session_id}/galleries/{gallery_id}
POST /api/emergent-tastes/sessions/{session_id}/galleries/{gallery_id}/cells/{cell_id}/activate
```

## License

Art Optimizer code is licensed under the [MIT License](LICENSE). Model checkpoints,
datasets, and generated-media obligations retain their own licenses.
