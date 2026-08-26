# Art Optimizer Roadmap

## Status

The repository now contains two different fixed-seed representation experiments:

```text
A. authored-axis search
   eight positive/negative prompt contrasts
   preference learning and emergent action modes

B. Random Direction Lab
   direct non-string prompt-embedding points
   four exact shell geometries
   iterative selected-point centering
   conditioning-variance receipts
```

The immediate product question is upstream and concrete:

> Which direct embedding-point geometry and radius produces useful, surprising visual movement at a fixed diffusion seed?

Do not expand taste ontology or planner complexity until that question is answered.

## Completed correctness gate

- experiment catalog and stable routes;
- no UI environment selector;
- neutral exploration separated from negative preference;
- preference-bearing rerolls receive restorable checkpoints;
- pending/final recovery for emergent preference facts;
- representation scopes include model, renderer, codec, conditioning mode, basis, prompt, seed, and dimension;
- mathematically consistent power-likelihood weighting;
- uniform-prevalence sticky-HMM baseline;
- convergence evaluated at one consistent parameter iterate;
- bounded gallery render concurrency and failure cleanup;
- local `make check` verification;
- hosted Actions removed.

## Completed direct-embedding implementation gate

Direction Lab implements four selectable codecs without authored direction strings:

1. full-tensor Gaussian points normalized to an exact shell;
2. exactly orthogonal full-tensor shell points;
3. structured rank-4 token-by-channel shell points;
4. an antipodal ± cross over two orthogonal random directions.

All four candidates share one diffusion seed. Radius is measured directly in units of base-prompt embedding RMS. The UI reports center displacement, pairwise point spacing, direction cosines, and effective rank. A selected point can become the exact center for the next shell.

See [`docs/RANDOM_EMBEDDING_CODECS.md`](docs/RANDOM_EMBEDDING_CODECS.md).

## Immediate real-model test gate

Use FLUX.2 Klein in embedding mode first. Hold one prompt and image seed fixed, then compare the four codecs at matched radii:

```text
0.10, 0.20, 0.40, 0.60, 0.80 × base embedding RMS
```

For each slate record:

- whether at least two images create a real preference decision;
- broken/off-manifold rate;
- same-image or common-mode collapse rate;
- subject preservation versus useful mutation;
- whether positive/negative antipodal pairs look meaningfully opposed;
- whether low-rank perturbations are more coherent than full-tensor noise;
- minimum useful radius and first destructive radius;
- latency and VRAM;
- prompt and point-seed sensitivity.

The first comparison should be visual and brutally practical. Do not add a downstream deduplicator to hide an unsuccessful codec.

## Promotion decision

After the first matrix, choose one of three outcomes:

### A. A random codec works

Promote the winning codec and calibrated radius range into a separate preference-learning treatment. Preserve Direction Lab as the untrained control.

### B. Only structured random points work

Expand the structured family—low-rank, covariance-shaped, or prompt-manifold residual—but keep exact shell normalization and matched variance.

### C. None works

Conclude that arbitrary prompt-embedding movement is too off-manifold for this model interface. Move to a better representation rather than adding optimizer machinery around bad coordinates.

## Later research gates

### 1. Preference learning over the winning random representation

Only after a codec passes, attach immutable choice facts and a small learner to a fixed basis instance. Basis refresh must restart or explicitly transport the posterior.

### 2. Retain useful directions

A selected movement remains provisional. Promote an unnamed reusable direction only after repeated support and held-out tests across independent centers and seeds.

### 3. Compare planner authority

Compare simple shell sampling, a learned target, and the existing authored-axis planner at matched generation budgets.

### 4. True image evolution

Add a separate parent-conditioned renderer treatment. Ordinary text-to-image navigation must remain described as generative-space search.

## Explicit non-goals

- hybrid same-root/fresh-root choice slates;
- generate-then-deduplicate perceptual reranking;
- string-authored “random” directions;
- sampling a near-center candidate in every slate;
- singleton concept promotion;
- treating Direction Lab selections as established tastes;
- claiming parent inheritance without parent-conditioned rendering.
