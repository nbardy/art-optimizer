# Art Optimizer

Art Optimizer is a local research application for fixed-root image search and human preference experiments.

## Experiments

Run one server and choose a treatment at:

```text
http://localhost:8000/
```

Stable routes:

```text
/ui/current-image       T0 authored-axis controlled-search baseline
/ui/implicit-lanes      T0 presentation variant
/ui/concept-shelf       T0 presentation variant
/ui/lane-board          T0 presentation variant
/ui/emergent-tastes     authored-axis latent preference modes
/ui/direction-lab       direct non-string random embedding points
```

There is no process-level UI selector. Experiment identity belongs in the route.

## Random Direction Lab

The original real-model test showed that the eight hand-authored prompt contrasts often produced changes that were too small and too predictable. Direction Lab changes that upstream representation directly.

It holds the prompt, model, inference settings, and diffusion seed fixed while placing four candidates on an explicit nonzero shell in the model's prompt-embedding tensor. It never creates candidate directions from strings such as “change color,” “change composition,” or “increase realism.”

Four selectable codecs are available:

```text
gaussian-shell     independent full-tensor Gaussian directions
orthogonal-shell   exactly orthogonal full-tensor Gaussian directions
low-rank-shell     structured rank-4 token × channel perturbations
antipodal-shell    +u, -u, +v, -v for two orthogonal random lines
```

For base prompt embedding \(e_0\), center offset \(x\), unit-RMS direction \(b_j\), and shell radius \(r\):

\[
e_j=e_0+\operatorname{RMS}(e_0)(x+r b_j).
\]

Every initial candidate is therefore exactly \(r\) base-RMS units from the prompt center. There is no center sample and no hidden dependence on embedding dimensionality. Selecting an image makes that exact embedding point the center of the next four-point slate while keeping the diffusion seed fixed.

The UI exposes the requested center offset, pairwise separation, direction cosine matrix, and effective rank before asking you to judge the images.

See [`docs/RANDOM_EMBEDDING_CODECS.md`](docs/RANDOM_EMBEDDING_CODECS.md).

## Authored-axis search and emergent modes

The ordinary search loop keeps the prompt, renderer, authored control basis, and world seed fixed. Candidate variance comes from movement in the original eight action/embedding coordinates.

The emergent treatment records exact fixed-root choice slates and fits a small sticky mixture of ideal-point choice models. The resulting Taste A/B/C cards are **action-preference modes** supported by chronological choices. They are not yet learned semantic attributes or tastes extracted directly from image embeddings.

Visible commands have distinct evidence semantics:

```text
Choose candidate    full candidate preference + navigation
None fit             weak anchor preference; no navigation
New directions       wider authored-axis proposals; no preference evidence
Resume exemplar      navigation only; no new evidence
```

Every preference-bearing reroll creates a recoverable branch checkpoint. Emergent observations use a durable pending/final protocol so a process crash after the base command can be repaired instead of dropping the vote.

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
- four direct random-embedding shell codecs;
- iterative choose-the-new-embedding-center exploration;
- exact conditioning-variance diagnostics;
- original fixed-root authored-axis search;
- exact candidate selection and branch history;
- exposure-aware T0 learner;
- replayable latent authored-action preference modes;
- seed-by-strength galleries;
- SQLite persistence and deterministic render manifests.

Not demonstrated:

- which random codec produces the most useful real-model images;
- a safe or calibrated radius for FLUX/Krea across prompts;
- visual tastes learned directly from image sets;
- reusable learned embedding directions;
- taste-authoritative candidate planning;
- parent-conditioned image evolution.

Those remain empirical research questions, not hidden implementation TODOs. See [`ROADMAP.md`](ROADMAP.md).

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

Direction Lab requires a real Diffusers model in embedding mode. The procedural renderer deliberately returns a clear unsupported-treatment message.

## Local open-weight models

```bash
pip install -e '.[dev,models]'
```

FLUX.2 Klein:

```bash
ART_OPTIMIZER_MODEL=flux2-klein \
ART_OPTIMIZER_CONDITIONING_MODE=embedding \
ART_OPTIMIZER_DEVICE=cuda \
ART_OPTIMIZER_DTYPE=bfloat16 \
ART_OPTIMIZER_IMAGE_SIZE=1024 \
python -m art_optimizer.app --host 127.0.0.1 --port 8000
```

Krea 2 Turbo:

```bash
ART_OPTIMIZER_MODEL=krea2-turbo \
ART_OPTIMIZER_CONDITIONING_MODE=embedding \
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
