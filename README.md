# Art Optimizer

Art Optimizer is a local research application for fixed-root image search and human preference experiments.

## Experiments

Run one server and choose a treatment at:

```text
http://localhost:8000/
```

Stable routes:

```text
/ui/current-image       T0 controlled-search baseline
/ui/implicit-lanes      T0 presentation variant
/ui/concept-shelf       T0 presentation variant
/ui/lane-board          T0 presentation variant
/ui/emergent-tastes     fixed-root latent preference modes
```

There is no process-level UI selector. Experiment identity belongs in the route.

## Current product contract

The ordinary search loop keeps the prompt, renderer, control basis, and world seed fixed. Candidate variance comes from movement in the declared action/embedding coordinates.

The emergent treatment records exact fixed-root choice slates and fits a small sticky mixture of ideal-point choice models. The resulting Taste A/B/C cards are **action-preference modes** supported by chronological choices. They are not yet learned semantic attributes or tastes extracted directly from image embeddings.

Visible commands have distinct evidence semantics:

```text
Choose candidate    full candidate preference + navigation
None fit             weak anchor preference; no navigation
New directions       wider proposals; no preference evidence
Resume exemplar      navigation only; no new evidence
```

Every preference-bearing reroll now creates a recoverable branch checkpoint. Emergent observations use a durable pending/final protocol so a process crash after the base command can be repaired instead of dropping the vote.

## Taste galleries

Click an exposed taste to inspect:

```text
rows      deterministic seeds
columns   scalar strengths of the fitted taste center
```

For center \(\theta_k\) and strength \(s\):

\[
a(s,k)=\operatorname{clip}(s\theta_k,-1,1).
\]

Gallery browsing creates no preference evidence. Rendering is concurrency-bounded, deterministic by manifest, and cleans newly created partial artifacts if a cell fails. Continuing from a cell starts a fresh fixed-root session with zero copied votes.

See [`docs/TASTE_GALLERIES.md`](docs/TASTE_GALLERIES.md).

## Honest boundary

Implemented:

- local procedural renderer;
- local FLUX.2 Klein and Krea 2 Turbo adapters;
- fixed-root action/embedding search;
- exact candidate selection and branch history;
- exposure-aware T0 learner;
- replayable latent action-preference modes;
- seed-by-strength galleries;
- SQLite persistence and deterministic render manifests.

Not demonstrated:

- validated semantic independence of the eight authored controls;
- visual tastes learned directly from image sets;
- reusable learned embedding directions;
- taste-authoritative candidate planning;
- parent-conditioned image evolution.

Those remain research gates, not hidden implementation TODOs. See [`ROADMAP.md`](ROADMAP.md).

## Quick start

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make check
make dev
```

Open `http://localhost:8000/`.

## Local open-weight models

```bash
pip install -e '.[dev,models]'
```

FLUX.2 Klein:

```bash
ART_OPTIMIZER_MODEL=flux2-klein \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 127.0.0.1 --port 8000
```

Krea 2 Turbo:

```bash
ART_OPTIMIZER_MODEL=krea2-turbo \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 127.0.0.1 --port 8000
```

## Verification

Hosted GitHub Actions is intentionally not part of this repository. The explicit local gate is:

```bash
make check
```

With a server running:

```bash
make smoke
```

## License

Art Optimizer code is MIT licensed. Model checkpoints, datasets, and generated-media obligations retain their own licenses.
