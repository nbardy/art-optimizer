# Art Optimizer

Art Optimizer is a local, human-in-the-loop system for evolving images through lightweight visual preference feedback.

The interaction is intentionally small:

1. one committed design fills the canvas;
2. four candidate descendants stream into the corners;
3. hover or hold previews a candidate at full size;
4. click or tap commits it;
5. reroll says the current design beats the exposed alternatives;
6. favorite adds durable evidence to a multimodal taste atlas;
7. **New world** changes the stochastic root while retaining persistent taste;
8. recent committed designs can be restored and forked.

## Status

The repository contains a runnable CPU reference implementation and local open-weight model stacks for:

- `procedural` — deterministic CPU renderer used by tests and UI development;
- `flux2-klein` — FLUX.2 Klein 4B through `Flux2KleinPipeline`;
- `krea2-turbo` — Krea 2 Turbo through `Krea2Pipeline`.

FLUX and Krea run locally through Diffusers. There is no hosted-model API adapter. The default real-model codec builds eight semantic directions directly in prompt-embedding space; a prompt-string fallback remains available for comparison.

## Quick start: CPU reference renderer

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
make dev
```

Open `http://localhost:8000`.

Runtime state is written to `.art-optimizer/`. The procedural renderer remains the default because it is deterministic, fast, and exercises the full UI, optimizer, persistence, streaming, and taste-atlas loop without a GPU.

## Local open-weight models

Install the optional local-model stack:

```bash
pip install -e ".[dev,models]"
```

A Hugging Face token may be required to download a gated checkpoint:

```bash
export HF_TOKEN=...
```

### FLUX.2 Klein 4B

```bash
ART_OPTIMIZER_MODEL=flux2-klein \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 0.0.0.0 --port 8000
```

### Krea 2 Turbo

```bash
ART_OPTIMIZER_MODEL=krea2-turbo \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 0.0.0.0 --port 8000
```

For constrained VRAM:

```bash
export ART_OPTIMIZER_CPU_OFFLOAD=1
```

To require pre-downloaded files and prevent network model downloads:

```bash
export ART_OPTIMIZER_LOCAL_FILES_ONLY=1
```

To pin a specific Hugging Face model revision for reproducible research:

```bash
export ART_OPTIMIZER_MODEL_REVISION=<commit-or-tag>
```

To compare against ordinary prompt compilation instead of embedding directions:

```bash
export ART_OPTIMIZER_CONDITIONING_MODE=prompt
```

The model registry is available at `GET /api/models`, and the active model, codec, conditioning mode, replay level, and license identifier are reported by `GET /healthz`.

### License note

Both targets expose local weights and internals. FLUX.2 Klein 4B uses Apache-2.0. Krea 2 uses the **Krea 2 Community License**, not an OSI-approved open-source license. Its community terms include a company-wide revenue threshold for commercial use and require content filtering for deployments. Read the model metadata returned by `/api/models` and the upstream license before deployment.

## Embedding codec

The optimizer works in one canonical action space:

\[
a \in [-1,1]^8.
\]

The shared axes are:

1. close-up ↔ expansive composition;
2. organic ↔ geometric form;
3. cool/restrained ↔ warm/saturated palette;
4. soft/diffuse ↔ dramatic/directional lighting;
5. minimal ↔ intricate detail;
6. matte/painterly ↔ glossy/translucent material;
7. still/orderly ↔ dynamic/turbulent motion;
8. abstract/stylized ↔ materially realistic rendering.

For each world prompt, the codec encodes a base prompt and positive/negative endpoint prompts for each axis. It forms local text-embedding directions:

\[
d_i = \frac{1}{2}\left(E(p_i^+) - E(p_i^-)\right),
\]

RMS-normalizes those directions, and applies the selected quantities:

\[
E(a) = E(p_0) + \frac{\eta}{\sqrt d}\sum_i a_i d_i.
\]

FLUX and Krea have small model-specific conditioning adapters because their embedding tensors and masks differ. Everything else—the action type, codec plan, renderer request, persistence, planner, and UI contract—is shared.

This is a versioned experimental control basis. It still needs coordinate-sweep and human-evaluation receipts before being described as a validated semantic space.

## Running on a remote node

Yes. The server and browser use ordinary HTTP plus Server-Sent Events, and generated images are served by the same process.

The safest development setup is an SSH tunnel:

```bash
# On the GPU node
python -m art_optimizer.app --host 127.0.0.1 --port 8000

# On your laptop
ssh -L 8000:127.0.0.1:8000 user@your-node
```

Then open `http://localhost:8000` on your laptop.

For direct LAN/VPC access, bind to `0.0.0.0`, allow the port in the node firewall/security group, and browse to `http://NODE_IP:8000`.

The development server currently has no built-in authentication or TLS. Do not expose it directly to the public Internet. Use an SSH tunnel, VPN, or authenticated HTTPS reverse proxy.

## Modularity

The implementation has narrow boundaries rather than model-specific branches throughout the service:

```text
canonical action
    -> SemanticDirectionCodec
    -> model-specific embedding adapter
    -> ImageRenderer
    -> RenderedArtifact
```

- **Models/codecs:** selected from one data registry. Adding a model means one profile and, only when tensor signatures differ, one small conditioning adapter.
- **Renderer:** the service depends on the `ImageRenderer` protocol.
- **Preference learner:** isolated in `preference.py`.
- **Acquisition policy:** isolated in `planner.py`.
- **Persistent memory:** isolated in `atlas.py`.
- **UI:** consumes versioned HTTP/SSE projections and can be replaced without importing optimizer or model code. Set `ART_OPTIMIZER_STATIC_DIR` to serve another client build.

The current server selects one render stack at process startup so only one large checkpoint occupies GPU memory. Algorithm and UI A/B harnesses can share the same persisted event facts; runtime hot-swapping of multiple giant checkpoints in one process is intentionally not part of v0.

## Optimizer

The current design is the anchor. A quadratic feature map is used:

\[
\psi(a)=
[a_1,\ldots,a_d,\;a_1^2,\ldots,a_d^2,\;\{a_i a_j\}_{i<j}].
\]

The branch-local utility model is:

\[
f(a)=w^\top\psi(a),
\qquad q(w)=\mathcal N(\hat w,\Sigma_w).
\]

Selecting one candidate is modeled as one multinomial choice among the anchor and meaningfully exposed candidates. Reroll selects the anchor as the outside option. A finite proposal pool combines local Gaussian points, scrambled Sobol coverage, posterior sampling, uncertainty, diversity, and compatible taste-atlas guidance.

The displayed quartet has four roles:

1. best local continuation;
2. diverse posterior sample;
3. informative uncertainty probe;
4. controlled surprise or another persistent taste mode.

## Persistence and replay

SQLite stores session projections, branch checkpoints, raw interaction events, command results, learner snapshots, and the preference atlas. PNGs are accompanied by request manifests. Cached images are reused only when model, source, codec, control basis, prompt, seed, action, dimensions, and inference settings match.

Real-model data is namespaced by model ID by default, preventing a missing FLUX artifact from being silently regenerated by Krea after a server restart.

## Test

```bash
python -m compileall -q art_optimizer tests
node --check art_optimizer/static/app.js
ruff check art_optimizer tests
python -m pytest
```

With a server running:

```bash
python scripts/smoke_test.py http://localhost:8000
```

The normal test suite does not load model weights. Model codecs and embedding conditioning are tested with injected local fake pipelines.

## API

```text
GET  /healthz
GET  /api/models
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

## License

The Art Optimizer code is licensed under the [MIT License](LICENSE). Model checkpoints, datasets, uploaded references, and generated-media obligations retain their own licenses.
