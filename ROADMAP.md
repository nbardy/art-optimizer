# Art Optimizer Roadmap

## Status

The testable product is now intentionally narrow:

```text
fixed root
+ action/embedding variance
+ truthful commands
+ durable choice facts
+ latent action-preference modes
+ read-only seed-by-strength inspection
```

Feature expansion is frozen until this loop has been tested with real models and users.

## Completed cleanup gate

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

## Immediate test gate

Run the existing UI with the intended FLUX/Krea configuration. Record:

- candidate usefulness and visible movement;
- `None fit` and `New directions` rates;
- whether inferred modes remain coherent over time;
- whether galleries reveal stable families across seed and strength;
- latency, VRAM, and failure behavior;
- any point where UI language exceeds what the system actually inferred.

Do not change planner authority, add image embeddings, or add another UI during this test.

## Remaining research gates

### 1. Validate the representation

Run fixed-seed sweeps over all authored controls across multiple prompts, seeds, strengths, models, and conditioning modes. Measure response, monotonicity, redundancy, clipping, and off-target drift.

A preference model is only as meaningful as the coordinates it observes.

### 2. Compare planner authority

Only after representation validation, create a separate treatment where the selected latent mode proposes candidates. Keep the current T0-planner treatment unchanged as the control.

### 3. Extract reusable directions

Pool repeated successful interventions, retain candidates provisionally, and promote an unnamed direction only after held-out fixed-root and cross-seed transfer tests.

### 4. True image evolution

Add a separate parent-conditioned renderer treatment. Ordinary text-to-image navigation must remain described as generative-space search.

## Explicit non-goals for the current treatment

- hybrid same-root/fresh-root choice slates;
- generate-then-deduplicate perceptual reranking;
- singleton concept promotion;
- semantic names inferred from action-space clusters;
- treating gallery clicks as preference observations;
- claiming parent inheritance without parent-conditioned rendering.
