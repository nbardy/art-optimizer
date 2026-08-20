# Art Optimizer

**Art Optimizer** is an open-source, human-in-the-loop system for evolving images through lightweight visual preference feedback.

The interaction stays deliberately small:

1. one committed design fills the canvas;
2. four candidate descendants stream into the corners;
3. hover or hold previews a candidate at full size;
4. click or tap commits it;
5. reroll says the current design beats the exposed alternatives;
6. favorite adds durable evidence to a multimodal taste atlas;
7. New world changes the stochastic root while retaining persistent taste;
8. the last ten committed designs can be restored and forked.

## Status

The repository now contains a **runnable CPU reference implementation** of the complete v0 interaction and learning loop.

It includes:

- a FastAPI development server;
- Server-Sent Events that stream each candidate independently;
- a deterministic procedural art renderer with a smooth, global eight-dimensional control basis;
- immutable design states and branch checkpoints;
- SQLite events and persisted session projections;
- a Bayesian linear multinomial-choice model with a Laplace posterior;
- a finite Sobol/Gaussian proposal pool and four distinct candidate roles;
- reroll as the current-anchor outside option;
- an evolving multimodal persistent preference atlas;
- favorites, New world, history restore, and branch forking;
- a responsive one-canvas/four-corner browser interface;
- GPU-free unit and end-to-end service tests.

The procedural renderer is an honest development adapter, **not a diffusion model disguised as one**. It allows the product state machine, optimizer, streaming protocol, persistence, and taste atlas to run end to end while the real-model control-basis experiment is conducted. See [Implementation status](docs/IMPLEMENTATION_STATUS.md).

## Run locally

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m art_optimizer.app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

Open:

```text
http://localhost:8000
```

Choose another port with `--port` or:

```bash
PORT=8787 make dev
```

Runtime state is written to `.art-optimizer/` by default. To use another location:

```bash
ART_OPTIMIZER_DATA_DIR=/tmp/art-optimizer \
python -m art_optimizer.app --host 0.0.0.0 --port 8000
```

The default render size is 640×640. A smaller value is useful for very modest CPUs:

```bash
ART_OPTIMIZER_IMAGE_SIZE=384 make dev
```

## Docker

```bash
docker compose up --build
```

Then open `http://localhost:8000`. The Compose configuration persists SQLite state and rendered assets in a named volume.

## Test

```bash
python -m pytest
node --check art_optimizer/static/app.js
```

With a server already running:

```bash
python scripts/smoke_test.py http://localhost:8000
```

## What the optimizer does

Each world owns one bounded absolute action vector:

\[
a \in [-1,1]^8.
\]

The current design is the anchor. A quadratic feature map is used:

\[
\psi(a)=
[a_1,\ldots,a_d,\;a_1^2,\ldots,a_d^2,\;\{a_i a_j\}_{i<j}].
\]

The branch-local utility model is:

\[
f(a)=w^\top\psi(a),
\qquad
q(w)=\mathcal N(\hat w,\Sigma_w).
\]

For one round, the alternatives are the current anchor plus the meaningfully exposed candidates. Selecting candidate \(j\) is modeled with a multinomial-logit likelihood. Reroll selects the anchor as the outside option. The posterior is updated with a damped Newton/Laplace step.

A hidden finite proposal pool combines local Gaussian perturbations, scrambled Sobol coverage, and declared persistent-atlas guidance. Four role-specific candidates are selected:

1. best local continuation;
2. diverse posterior sample;
3. informative uncertainty probe;
4. controlled surprise or another persistent taste mode.

## Persistent taste atlas

Persistent taste is a set of coherent modes, not one average embedding.

- ordinary commits provide weak evidence;
- revisits provide moderate evidence;
- favorites provide strong evidence;
- strong novel evidence may create a new mode;
- weak novel evidence remains provisional until several coherent events support it;
- New world samples from known taste while reserving nonzero probability for outside-prior exploration.

The current procedural adapter has a declared globally stable control basis, so an atlas component may provide a world-level action bias. A real diffusion adapter must not assume such transfer: it should install fixed exemplar/reference coordinates or another experimentally validated transport into the world control basis.

## API

The browser uses ordinary idempotent-style HTTP commands and an SSE stream:

```text
POST /api/sessions
GET  /api/sessions/{session_id}
GET  /api/sessions/{session_id}/events
POST /api/sessions/{session_id}/candidates/{candidate_id}/commit
POST /api/sessions/{session_id}/reroll
POST /api/sessions/{session_id}/new-world
POST /api/sessions/{session_id}/designs/{design_id}/favorite
POST /api/sessions/{session_id}/history/{branch_node_id}/restore
GET  /api/sessions/{session_id}/event-log
GET  /healthz
```

Images are served from `/assets/...`; SSE snapshots reveal each URL as soon as that candidate is durable and ready.

## Repository layout

```text
art_optimizer/
  app.py          FastAPI routes and static serving
  service.py      session coordinator and streaming workflows
  domain.py       immutable state and event-facing contracts
  preference.py   multinomial Bayesian learner
  planner.py      finite-pool, four-role acquisition policy
  atlas.py        persistent multimodal taste memory
  renderer.py     deterministic procedural renderer adapter
  event_store.py  SQLite events and projections
  static/         one-canvas/four-corner interface

tests/            optimizer, atlas, renderer, API, and end-to-end service tests
scripts/          smoke testing
```

## Normative design documents

1. [Interaction model v0](docs/INTERACTION_MODEL_V0.md)
2. [State and control contract](docs/STATE_AND_CONTROL_CONTRACT.md)
3. [V0 algorithm specification](docs/V0_ALGORITHM_SPEC.md)
4. [Persistent preference atlas](docs/PERSISTENT_PREFERENCE_ATLAS.md)
5. [Implementation readiness](docs/IMPLEMENTATION_READINESS.md)
6. [Control-basis experiment](docs/CONTROL_BASIS_EXPERIMENT.md)
7. [Implementation status](docs/IMPLEMENTATION_STATUS.md)

Additional background lives in [Research notes](docs/RESEARCH_NOTES.md), [Architecture](docs/ARCHITECTURE.md), [Code design](docs/CODE_DESIGN.md), and [UI design](docs/UI_DESIGN.md).

## Real-model boundary

The next research vertical is a renderer adapter for an open fast image model. It must pass the repository's control-basis gate before becoming the default:

- deterministic or declared replay level;
- fixed world-level conditions and controls;
- smooth and useful coordinate sweeps;
- enough nonredundant directions;
- meaningful within-round diversity;
- preservation behavior;
- measured batch-of-four latency and memory;
- no hidden per-candidate prompt, seed, reference, or adapter changes.

Until then, the CPU renderer is the supported executable reference for the interaction and learning system.

## License

The code is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, and uploaded references retain their own licenses.
