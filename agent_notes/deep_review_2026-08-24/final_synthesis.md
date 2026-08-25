# Final Synthesis

## Review base and confidence

This synthesis audits [`main@893e404`](https://github.com/nbardy/art-optimizer/commit/893e4049105ac56a829edadface3a35a61d087d5). It reconciles independent passes over architecture, type/data flow, frontend sharing, design completeness, persistence/concurrency, gallery/renderer behavior, mathematical formulation, and numerical correctness.

Confidence is high for findings tied directly to code paths. Claims about real FLUX/Krea visual quality remain untested because the model benchmark has not been run here.

## Overall verdict

Art Optimizer contains a strong product/research idea and several good implementation seams, but the current `main` is still a **research prototype whose runtime is less complete and less mathematically correct than its descriptions imply**.

The clean system inside the repository is:

```text
fixed-root renderer context
+ typed choice slate
+ honest command semantics
+ one preference projection
+ seed-by-strength inspection
+ immutable experiment receipts
```

The current system surrounds that with:

- one oversized mutable service;
- four overlapping preference representations;
- duplicated browser controllers;
- incomplete treatment/state identity;
- crash windows between base and emergent evidence;
- heuristic latent-mode inference with real mathematical errors;
- unvalidated authored embedding geometry.

This should not be thrown away. It should be **contracted around the working core** before further product expansion.

## Scorecard

| Area | Assessment | Bottom line |
|---|---|---|
| Code quality | C- prototype | readable local modules, poor orchestration boundaries and substantial duplication |
| Design completeness | partial | most visible emergent/gallery UX exists; stronger image-set taste model does not |
| Bug risk | high for research evidence | ordinary demo can run, but preference facts and recovery are not trustworthy enough for authority |
| Mathematical model | promising baseline | problem needs a formal landscape and modular mathematical interfaces |
| Mathematical correctness | mixed | ideal-point gradient correct; sticky-HMM fitting/model selection contain substantive errors |
| Representation validity | unproven | authored prompt-embedding axes have not passed effect, monotonicity, redundancy, or transfer tests |

## The ten most important findings

### 1. Critical: a qualified emergent vote can be permanently lost

The base command commits before the emergent event is appended. A process death in between leaves a durable design/legacy update and no replayable taste fact. Retry cannot reconstruct the old slate from current state.

Evidence: [`emergent_experiment.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_experiment.py), `commit_candidate` and `none_of_these`.

### 2. High: `None fit` learning is not checkpointed

The base reroll path changes posterior/search state without creating a branch checkpoint. Restoring that branch later reloads an older posterior and silently discards those observations.

Evidence: [`service.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py), `reroll` versus `restore`.

### 3. High: the sticky-HMM prevalence update is mathematically wrong

The declared transition is:

\[
T_{ij}=\rho\mathbf1[i=j]+(1-\rho)\pi_j.
\]

The implementation updates \(\pi\) from state occupancy counts, as if the model were an exchangeable mixture. The correct M-step depends on expected transition counts and the nonlinear diagonal term.

Evidence: [`emergent_taste.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py), `_run_em` and `_transition_matrix`.

### 4. High: EM convergence is evaluated on mismatched parameters

The code combines an old-parameter likelihood with a new-center prior penalty, then uses it as the convergence objective. It is not the objective at either iterate.

### 5. High: gallery execution is unbounded and non-recoverable

A maximum gallery launches 42 `to_thread` calls in one `gather`. One failure loses the response while successful artifacts remain orphaned. There is no progress, cancellation, queue, or partial result.

Evidence: [`taste_gallery.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/taste_gallery.py), `generate`.

### 6. High: experiment and representation scope are incomplete

Sessions and observations do not consistently pin model source/checkpoint, image size, dtype, inference settings, embedding strength, direction-bank instance, and numerical policy. Atlas grouping omits renderer revision even though evidence stores it.

### 7. High: the emergent treatment is not isolated

Emergent choices still update the legacy 44-parameter learner and persistent atlas. The atlas can influence initial roots and candidate proposals. The new taste projection is therefore a shadow layered over legacy preference behavior, not a clean independent treatment.

### 8. Medium-high: current “taste” is not extracted from image sets

The latent model sees action coordinates and choices. Images are selected as exemplars after fitting. There is no visual likelihood, visual consistency score, or held-out cross-seed family test.

The honest current object is an **emergent action-preference mode**.

### 9. Medium-high: user-visible taste identity is unstable

All `K` models refit from scratch. A warm-start alignment method exists but is never used. Taste A/B/C are assigned from current hard assignments and first-seen order, so labels and exemplars can switch retroactively.

### 10. Medium-high: frontend infrastructure is duplicated

The baseline, emergent, concept, and gallery controllers each implement overlapping API, session, SSE, exposure, preview, history, busy, and recovery logic. The gallery infers identity by parsing the visible label `Taste A` and attaches itself with a mutation observer.

## How much slop and extra code?

### Backend

The main slop is orchestration, not low-level algorithms. `ArtOptimizerService`, `EmergentTasteExperiment`, and `TasteGalleryService` repeat transaction and projection protocols and cross private boundaries.

A pure reducer + one command executor + bounded job coordinator can plausibly reduce this slice to **45–60% of its current size** while improving correctness.

### Frontend

Shared session, SSE, exposure, candidate, and history modules can plausibly remove **40–55% of controller code**.

### Whole repository

A 2× whole-repository reduction is possible only if the legacy concept UIs/atlas path are quarantined or retired. A 5× goal would mean deleting experiments and evidence, not merely writing better abstractions. It should not be a quality metric.

## Fallbacks and branching

The issue is not the raw presence of `if` or `try`. The issue is **where uncertainty is resolved**.

Current high-risk examples:

- missing model prediction receipt becomes uniform probability;
- chosen-but-unexposed candidates are silently repaired;
- non-finite planner scores become the first available candidate;
- invalid gallery strengths are silently filtered in the browser;
- any resume error deletes session identity;
- request ID reuse with a different payload returns the previous result;
- broad renderer exceptions become untyped strings.

A cleaner system branches once on typed unions and fails construction for impossible states.

## What is genuinely good

This review should not erase the parts worth retaining:

1. The fixed-root versus seed-gallery separation is conceptually clean.
2. `New directions` versus `None fit` is the right command distinction.
3. The renderer protocol and model registry are good seams.
4. Pydantic validation catches many shape/value failures early.
5. Render artifacts use request digests and atomic file writes.
6. The ideal-point component likelihood is compact and its center gradient is correct.
7. Prequential prediction before fitting the outcome is the right evaluation direction.
8. The gallery creates fresh sessions without copying preference votes.
9. T0 is preserved as a baseline rather than silently overwritten.
10. Tests already cover core happy paths and deterministic synthetic examples.

## Design-completeness conclusion

### Implemented

- experiment catalog;
- fixed-root four-candidate loop;
- embedding/action variation;
- truthful emergent command vocabulary;
- finite sticky latent preference modes;
- taste cards and exemplars;
- seed-by-strength gallery;
- no-vote gallery browsing;
- fresh session from selected gallery cell.

### Partial

- continuous train/test: only observed-winner prequential probability, no full calibration;
- replay: emergent projection replays, whole experiment does not;
- provenance: many fields, incomplete scope identity;
- tastes: latent action modes, not image-family models;
- experiment isolation: legacy learner and atlas remain active.

### Not implemented

- session-scoped configurable ablations and policy digests;
- stable taste revisions/lineage;
- posterior uncertainty for ideal points;
- visual/image-set taste extraction;
- reusable learned directions;
- taste-authoritative planning;
- true parent-conditioned image evolution;
- full crash-consistent command/evidence transaction;
- bounded recoverable render jobs;
- real model control-basis validation.

## Mathematical conclusion

### Correct

- ideal-point softmax likelihood;
- center gradient sign and scaling;
- positive-definite MAP objective under Gaussian prior;
- basic forward/backward scaling for a fixed transition matrix;
- legacy multinomial logistic Fisher structure.

### Incorrect or materially incomplete

- sticky prevalence M-step;
- EM convergence objective;
- consistency of weak observation weighting between fit and score;
- posterior-predictive claim;
- model complexity penalty;
- stable component identity;
- calibrated action geometry;
- exact Bayesian/replay interpretation of legacy learner;
- full prediction/calibration receipts.

## Repository-authority warning

The audited `main` does not contain several capabilities described in prior delivery prose, including session-configurable taste ablations, Laplace-QMC prediction, corrected prevalence inference, a removed GitHub Actions workflow, or the claimed final finish-plan documents. The source tree at the audited SHA is the authority.

Future status updates should be generated from a checked commit and should distinguish:

```text
implemented on main
implemented on an open branch
locally drafted
specified in documents
proposed only
```

## Decision

Do **not** add another UI or another preference model now.

Freeze feature work and complete three gates in order:

1. **Evidence correctness:** atomic/recoverable commands, checkpoint semantics, typed scopes, bounded render jobs.
2. **Mathematical correctness:** fix or simplify HMM inference, posterior prediction, model identity, and adversarial tests.
3. **Representation validity:** demonstrate that the authored embedding coordinates produce useful controlled visual movement on real models.

Only after those gates should an emergent taste become authoritative for candidate planning or be described as a discovered visual taste.
