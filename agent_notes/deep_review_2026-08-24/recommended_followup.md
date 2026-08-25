# Recommended Follow-up

## Guiding principle

The next work should make the existing experiment **smaller, truer, and falsifiable**. It should not add more surfaces.

Recommended order:

```text
correct facts and recovery
→ simplify state and treatment ownership
→ correct mathematical inference
→ validate the representation
→ only then change candidate authority
```

## PR 1 — Invariant and failure-injection tests

### Purpose

Convert the highest-severity review findings into failing tests before refactoring.

### Add tests for

1. crash after a base candidate commit but before emergent event append;
2. crash after anchor-win base update but before emergent append;
3. command retry after mutation but before command-result receipt;
4. several `None fit` updates followed by branch restore;
5. restart with `transition_id` left in progress;
6. same request ID with a different command payload;
7. concurrent identical gallery requests;
8. partial gallery render failure and artifact cleanup;
9. activation retry returning byte-equivalent response data;
10. renderer cache race for identical requests;
11. missing prediction receipt must fail replay;
12. small HMM likelihood/posterior compared with brute-force hidden paths;
13. finite-difference ideal-point gradient/Hessian;
14. EM observed-objective monotonicity.

### Acceptance

Every critical/high issue has a deterministic failing regression test. No feature behavior changes yet.

## PR 2 — Typed command/event transaction core

### Purpose

Make one logical command equal one recoverable fact and one stable response.

### Implement

- discriminated command union;
- discriminated event union with schema revision;
- canonical command payload digest;
- `RepresentationScope` and `TreatmentAssignment` types;
- one repository transaction method per command use case;
- event-first pending/final protocol or one physical SQLite transaction;
- command receipt committed with authoritative mutation;
- immutable preference checkpoint for non-navigation updates;
- recovery reducer for pending commands and stranded world transitions.

### Retire

- silent chosen-exposure repair;
- uniform fallback for missing prediction receipts;
- `expected_version` inside the core command type;
- raw event payload dictionaries in model code.

### Acceptance

```text
same request + same payload -> exact original result
same request + different payload -> conflict
process death at any boundary -> deterministic recovery
history restore -> no preference evidence silently disappears
```

## PR 3 — Bounded render-job subsystem

### Purpose

Replace cancellable wrapper tasks and blocking gallery fan-out with explicit jobs.

### Implement

```text
RenderJob
RenderCellJob
queued/running/succeeded/failed/obsolete/cancelled
bounded worker count
request-digest deduplication
per-cell gallery progress
partial failure receipts
cooperative/declared non-cooperative cancellation
artifact liveness and cleanup
```

The renderer is an effect handler. Session reducers enqueue jobs but do not own threads.

### Frontend

- stream candidate/gallery progress;
- gallery can always close;
- explicit cancel or continue-in-background policy;
- partial successful cells remain usable.

### Acceptance

No command launches unbounded `to_thread` work. Obsolete GPU renders cannot masquerade as cancelled. Partial failures do not orphan untracked artifacts.

## PR 4 — Treatment isolation and state cleanup

### Purpose

Make `/ui/emergent-tastes` a real experiment rather than a wrapper around three legacy preference systems.

### Add frozen treatment policy

```python
TreatmentConfiguration(
    root_policy="neutral" | "declared_atlas",
    candidate_planner="legacy_t0",
    branch_learner="shadow" | "disabled",
    persistent_atlas_reads=False,
    persistent_atlas_writes=False,
    emergent_engine_policy=...,
    command_semantics=...,
)
```

### Separate commands

- revisit image with current preference state;
- fork exact historical experiment checkpoint.

### Quarantine legacy code

Move browser `ConceptLibrary` and atlas-driven concept treatments behind an explicit `legacy_t0` boundary. Keep them runnable, but stop allowing them to leak into new-treatment state.

### Acceptance

The treatment receipt is enough to state exactly which engine planned, learned, and persisted every interaction.

## PR 5 — Correct mathematical baseline

### Purpose

Produce one boring, correct emergent-taste engine before adding flexible models.

### Recommended v1 simplification

Use:

```text
K in {1,2,3}
ideal-point utility
fixed calibrated Q
uniform base prevalence
fixed stickiness
Gaussian center prior
joint MAP/EM with correct objective
Laplace center covariance
full categorical prequential predictions
```

Uniform prevalence avoids the current incorrect M-step. Add optimized prevalence only as a later explicit ablation with expected transition counts and constrained optimization.

### Required changes

- recompute observed objective after every M-step;
- record convergence diagnostics;
- calculate Hessian/covariance;
- deterministic QMC posterior prediction or clearly named MAP plug-in mode;
- make weak-observation semantics consistent between fit and score;
- full probability vectors in prequential receipts;
- stable component revisions matched to prior state/evidence lineage;
- model comparison based on prequential performance plus a simulation-calibrated split threshold;
- no silent receipt fallback.

### Acceptance

- brute-force HMM tests pass;
- gradient/Hessian tests pass;
- simulations recover known one/two/three-mode cases;
- false split rate is measured;
- calibration is reported;
- replay is invariant within declared tolerance.

## PR 6 — Shared frontend client and components

### Purpose

Reduce controller duplication after semantics are stable.

### Extract

- `session_client.js`;
- `candidate_exposure.js`;
- `candidate_grid.js`;
- `history_view.js`;
- typed treatment adapter interface;
- normal taste-card/gallery callback integration.

### Remove

- label parsing (`Taste A -> taste-1`);
- gallery `MutationObserver` surgery;
- duplicate API/SSE/recovery implementations;
- silent session deletion on non-404 resume errors;
- visible planner role labels in ordinary experiment mode.

### Expected impact

40–55% fewer frontend controller lines, with one behavior implementation for exposure, retries, and conflicts.

## PR 7 — Representation benchmark and geometry

### Purpose

Determine whether the current authored axes deserve to be the space in which tastes are learned.

### Matrix

For FLUX and Krea, across prompts and seeds:

- positive/negative strength sweeps;
- effect magnitude;
- monotonicity;
- sign consistency;
- direction redundancy/condition number;
- off-target drift;
- Krea mask behavior;
- single-axis scaling with/without `1/sqrt(d)`;
- latency/VRAM;
- human usefulness.

### Compare

- authored embedding directions;
- prompt-only controls;
- isotropic random directions;
- prompt-manifold directions;
- neutral/seed controls.

### Output

A versioned `ActionGeometry`/basis manifest with:

- retained directions;
- per-axis scale;
- validity region;
- metric or whitening transform;
- rejected directions and reasons.

### Acceptance

At least one representation produces reproducible, useful, fixed-root visual movement. Until then, taste centers remain coordinates in an unvalidated intervention space.

## PR 8 — Taste-family validation, not another learner

### Purpose

Use the existing seed-by-strength gallery as a scientific probe.

### Add

- frozen component revision and uncertainty in gallery manifest;
- neutral and alternate-taste comparison rows;
- typed human judgments about family coherence;
- held-out seeds and anchors;
- cross-seed consistency metrics as diagnostics;
- explicit pass/fail `GenerativeFamilyValidationReceipt`.

Gallery interactions remain separate from ordinary preference evidence.

### Acceptance

A taste may be described as a generative image family only after held-out gallery evidence supports that claim.

## PR 9 — Taste-authoritative planner as a separate treatment

Only after PRs 1–8 pass.

Hold renderer, seed, UI, command vocabulary, candidate count, and budget fixed. Compare:

```text
legacy planner authoritative / emergent shadow
versus
emergent planner authoritative / legacy shadow
```

Evaluate prediction, acceptance rate, `None fit` rate, time to liked/exported result, coverage, collapse, and recovery.

Do not silently promote the existing route.

## What not to do next

- do not add another UI layout;
- do not add perceptual duplicate filtering as downstream cleanup;
- do not mix fresh seeds into the ordinary preference slate;
- do not implement a GP or neural taste model before the finite baseline is correct;
- do not call gallery similarity attribute extraction;
- do not make parent-conditioned evolution part of this refactor;
- do not optimize for a 5× repository line reduction;
- do not trust PR descriptions or status prose without checking the referenced commit.

## Suggested issue structure

Create or update narrow issues:

1. `P0 — crash-consistent choice facts and checkpoints`
2. `P0 — bounded render jobs and gallery recovery`
3. `P0 — correct sticky ideal-point baseline`
4. `P1 — isolate emergent treatment from atlas/legacy learners`
5. `P1 — consolidate browser session/exposure controllers`
6. `P1 — validate authored embedding basis on real models`
7. `P2 — held-out generative-family validation`
8. `P2 — taste-authoritative planner experiment`
9. `Later — reusable direction extraction`
10. `Separate product — true parent-conditioned evolution`

## Immediate recommendation

Start with PR 1 and PR 2 only. The current highest risk is not poor search quality; it is that the system can lose or reinterpret the very evidence needed to judge search quality.
