# Control-Basis Experiment

**Status:** Normative gate for selecting the first real renderer control manifold  
**Last updated:** 2026-08-20

## 1. Purpose

The optimizer requires a bounded, replayable, approximately smooth world-level action space. An image model being fast or visually strong does not prove that it exposes such a space.

This experiment selects the first real `ControlBasisManifest`. It is a blocking gate between the fake-renderer product shell and claims of useful image optimization.

## 2. Research question

For a candidate renderer, which control coordinates provide the best combination of:

- local perceptual responsiveness;
- continuity;
- useful diversity;
- content/preservation stability;
- low redundancy;
- replayability;
- fast batch-of-four inference?

The experiment compares control families and hybrids under identical prompts, roots, resolutions, and hardware receipts.

## 3. Candidate control families

### 3.1 Fixed reference-weight coordinates

At world creation, choose fixed reference identities and expose only their bounded weights as coordinates.

Sources may include:

- user-provided references;
- up to two persistent-atlas exemplars;
- a fixed style/composition reference bank for research baselines.

Reference identity cannot change inside a world.

### 3.2 Conditioning-embedding directions

A world may include fixed directions in the model's conditioning representation.

Possible construction methods:

- PCA/SVD over a declared prompt-embedding bank;
- differences between the base prompt and recorded prompt variants;
- learned directions imported from an earlier prototype;
- fixed random orthogonal directions as a control baseline.

The endpoints, tokenizer/text-encoder revision, layer, normalization, and interpolation rule are part of the basis manifest.

### 3.3 Adapter-weight coordinates

A fixed adapter/LoRA bank may provide bounded mixture weights:

$$
\theta(a)=\theta_0+\sum_i a_i\Delta\theta_i.
$$

Adapter identities and digests are fixed per world. Coordinates vary only weights.

### 3.4 Attention/intermediate-state directions

Model-specific directions may be applied to declared layers, heads, or Q/K/V/state tensors. The intervention point, basis tensor, timestep schedule, and scale rule are immutable manifest data.

These coordinates are experimental until they pass replay and local-sweep tests.

### 3.5 Tangent-space initial-noise coordinates

Optional world-local coordinates use the spherical tangent construction in `V0_ALGORITHM_SPEC.md`.

Noise coordinates remain disabled in the first semantic/control experiment and are added as a separate ablation.

## 4. Candidate basis configurations

At minimum compare:

| ID | Basis |
|---|---|
| B0 | random seed/root changes only; negative control |
| B1 | fixed root, conditioning directions |
| B2 | fixed root, reference weights |
| B3 | fixed root, adapter weights |
| B4 | fixed root, conditioning + reference hybrid |
| B5 | best semantic hybrid + tangent noise |
| B6 | parent-relative image editing; experimental non-v0 comparator |

B6 is measured because it may look good, but it is not accepted into the absolute-coordinate v0 optimizer unless it can compile a replayable world-level coordinate system.

## 5. Experiment corpus

Use a fixed, versioned corpus spanning at least:

- portrait/figure;
- architecture/interior;
- landscape/coastal;
- abstract/geometric;
- painterly/editorial;
- dense texture/particle systems;
- typography or graphic layout where supported.

For each category, include prompts with and without references and preservation locks.

Minimum initial matrix:

```text
20 world conditions
× 4 independent root-noise tensors
× candidate basis configurations
```

The exact corpus, safety filtering, and prompt licenses are stored in the experiment manifest.

## 6. Coordinate sweeps

For every coordinate \(i\), world \(w\), and at least three anchor actions, render:

$$
a_i\in\{-1,-0.5,0,0.5,1\},
$$

with all other coordinates fixed.

Also render small finite-difference probes:

$$
a\pm h e_i
$$

at several \(h\) values to estimate local sensitivity and catastrophic thresholds.

All sweep images share the exact world root, conditions, model, and basis.

## 7. Feature measurements

For rendered image feature map \(\phi(I(a))\), estimate the local Jacobian:

$$
J(a)_{:,i}
\approx
\frac{\phi(I(a+h e_i))-\phi(I(a-h e_i))}{2h}.
$$

Use a versioned feature bundle containing at least:

- semantic representation;
- style/texture representation;
- composition/structure representation;
- perceptual image distance;
- quality/artifact scores;
- preservation metrics where references or masks exist.

No single embedding determines acceptance.

## 8. Coordinate metrics

### 8.1 Responsiveness

Adjacent sweep points must create a detectable perceptual change:

$$
R_i=\operatorname{median}_{w,a}
D_\phi(I(a),I(a+h e_i)).
$$

Near-zero coordinates are removed.

### 8.2 Catastrophic rate

Measure the fraction of small steps causing:

- severe artifact score increase;
- unintended subject loss;
- layout collapse;
- safety refusal;
- discontinuous perceptual jump.

Coordinates with high catastrophic rate are removed or have their bounds reduced.

### 8.3 Local smoothness

For a five-point sweep, compare adjacent feature differences and second finite differences. A useful coordinate should not be required to be globally linear, but it should have a nontrivial local interval where changes are coherent.

### 8.4 Monotonicity proxy

Some coordinates have no named semantic target. Measure directional consistency in feature space:

$$
M_i=
\frac{1}{n-1}
\sum_t
\cos(\Delta\phi_t,\bar d_i).
$$

Low consistency indicates that one scalar coefficient does not represent a stable local direction.

### 8.5 Redundancy

Using the perceptual Gram matrix:

$$
G=J^TWJ,
$$

measure normalized off-diagonal similarity. Highly redundant coordinates are removed or combined.

### 8.6 Condition number

An ill-conditioned local metric means the optimizer sees several nearly identical directions and weakly observable axes. Track the spectrum of:

$$
M(a)=J(a)^TWJ(a)+\epsilon I.
$$

### 8.7 Preservation

When preservation locks are active, report:

- identity/reference similarity;
- segmentation/layout agreement;
- text/layout consistency where applicable;
- unintended semantic drift.

### 8.8 Transfer

Measure whether coordinate behavior survives:

- another root in the same condition;
- another prompt in the same category;
- another category;
- another model/runtime revision.

V0 does not require global semantic transfer, but the scope of every coordinate must be declared honestly.

## 9. Perceptual calibration

Raw coefficients need not correspond to equal visual amounts. For retained coordinates or directions, estimate perceptual arclength:

$$
s(\alpha)
=
\int_0^\alpha
\sqrt{d^TM(a+td)d}\,dt.
$$

Fit a monotone calibration map for candidate proposal distance and future user-facing quantity controls.

The optimizer may operate in normalized calibrated coordinates even before sliders are exposed.

## 10. Basis construction

Starting from candidate coordinates:

1. remove near-zero and high-catastrophe axes;
2. scale each coordinate by its useful local range;
3. estimate the median perceptual metric over calibration anchors;
4. remove highly redundant coordinates;
5. optionally orthogonalize under the perceptual metric;
6. retain at most sixteen coordinates;
7. regenerate sweeps in the final basis;
8. freeze the manifest and calibration receipt.

If orthogonalization creates linear combinations of model-specific controls, the compiler must record the exact transformation matrix.

## 11. Quartet test

A basis that passes one-dimensional sweeps may still produce bad slates.

For each calibration world, sample role-like quartets at several trust-region radii and measure:

- duplicate rate;
- median within-slate perceptual distance;
- artifact/catastrophe rate;
- preservation-lock failures;
- human judgment of “same world, meaningfully different”;
- render latency and batch isolation.

The default radius is selected from this test, not guessed from coefficient units.

## 12. Human evaluation

A small blinded evaluation should compare basis configurations using the actual one-image/four-corner UI.

For each round, ask:

- Are at least two candidates meaningfully different?
- Do they feel like plausible continuations of the current design?
- Is one candidate broken or unrelated?
- Does reroll feel necessary because of model sameness?
- Which basis makes it easiest to move intentionally?

Record selections and explicit post-round judgments separately.

## 13. Latency receipt

For each model/basis configuration, record:

```text
GPU and driver
runtime/container digest
model/checkpoint and adapter digests
dtype and quantization
resolution
batch size
step count and scheduler
warm/cold state
first preview latency
all-four preview latency
peak memory
feature-extraction latency
```

A visually excellent basis that misses the interaction latency budget may remain an export-quality tier rather than the main browser renderer.

## 14. Acceptance gate

A real control basis is accepted when:

1. at least eight coordinates survive responsiveness, smoothness, and catastrophe filtering;
2. replay passes at the declared level;
3. the median quartet has useful diversity without routine world-breaking jumps;
4. fixed atlas reference slots compile as ordinary declared coordinates when supported;
5. the local metric is not dominated by a single coordinate or a near-singular redundant block;
6. the basis outperforms seed-only/random-walk controls in blinded interaction;
7. latency and memory receipts are published;
8. all coordinate scopes and limitations are documented.

If only four to seven strong coordinates survive, the team may run a reduced-dimensional research build, but it must not pretend to have a richer manifold.

## 15. Outputs

The experiment produces:

- `ControlBasisManifest`;
- coordinate calibration receipts;
- model/runtime capability profile;
- sweep image/contact-sheet artifacts;
- feature and quality metrics;
- quartet benchmark report;
- latency receipt;
- accepted bounds and default trust-region radius;
- rejected-coordinate log with reasons.

## 16. Implementation artifacts

Suggested scripts:

```text
scripts/control_basis/build_basis.py
scripts/control_basis/render_sweeps.py
scripts/control_basis/extract_features.py
scripts/control_basis/analyze_jacobian.py
scripts/control_basis/render_quartets.py
scripts/control_basis/report.py
```

All outputs are content-addressed and reproducible from one experiment manifest.

## 17. Decision rule

Do not choose the renderer only from public text-to-image leaderboard quality.

Choose the model and basis that best support:

> fast, replayable, locally coherent movement through a parameterized visual world under repeated human choice.
