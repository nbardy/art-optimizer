# Random Soft-Direction Explorer

**Status:** Round 2 experiment proposal  
**Problem:** hand-authored prompt axes are narrow and may miss useful, non-string-promptable conditioning directions

## Hypothesis

A frozen image model may contain smooth, locally useful conditioning directions that are not cleanly represented by one natural-language prompt. Searching a calibrated low-dimensional random subspace around the current prompt embedding may discover visually useful movements beyond the eight authored axes.

This experiment does **not** assume arbitrary Gaussian directions are semantic. It asks whether a filtered and calibrated subset is useful for interactive search.

## Geometry

Let the base prompt-conditioning representation be:

\[
e_0\in\mathbb R^D.
\]

Choose a small basis:

\[
B=[b_1,\ldots,b_k],\qquad k\in\{8,12,16\},
\]

and search:

\[
e(u)=e_0+\frac{s}{\sqrt{k}}Bu,
\qquad u\in[-1,1]^k.
\]

High-dimensional Gaussian samples do not cluster near zero in norm; they concentrate near a shell and are approximately orthogonal. The real danger is that random directions are off-distribution, inert, entangled, or visually destructive.

## Basis families

### A. Isotropic local random

Draw random vectors matching the base representation’s dtype/shape, project away any prohibited dimensions, normalize, and calibrate by rendered effect.

### B. Prompt-manifold random

Encode a set of paraphrases and descriptive variations, estimate local covariance, and sample directions from that empirical covariance. These remain closer to language-induced variation while supporting continuous combinations not tied to one string.

### C. Residual random

Project random directions away from the span of authored axes and sampled prompt-manifold directions. This searches conditioning variation not explained by the known prompt controls.

### D. Retained successful directions

Carry forward directions with repeated positive evidence. Refresh unsuccessful or broken directions. A possible next basis is:

```text
50% retained successful
25% fresh prompt-manifold
25% fresh residual
```

The ratios are experimental parameters, not defaults to hard-code globally.

## Calibration

Raw directions have incomparable effect sizes. For each direction, render low-resolution probes at signed amounts and estimate:

\[
d_i(\alpha)=D_\phi(G(e_0),G(e_0+\alpha b_i)).
\]

Choose a scale \(s_i\) that reaches a target perceptual movement without crossing a broken/artifact threshold. Reject directions that are:

- inert across the safe range;
- catastrophically unstable;
- redundant with retained directions;
- dominated by rendering artifacts;
- non-repeatable under controlled roots.

Perceptual calibration should use output representations and human spot checks; text-embedding norm alone is insufficient.

## First treatment

A four-candidate slate can ask four different questions:

| Candidate | Conditioning policy | Root policy |
|---|---|---|
| A | current best subspace movement | same root |
| B | fresh prompt-manifold direction | same root |
| C | fresh residual direction | same root |
| D | current best composition | fresh or correlated root |

The role labels remain hidden in ordinary use but are logged.

## Commands

```text
Choose
    preference observation

More variety
    no preference observation
    refresh directions and/or stochastic roots

None of these
    weak outside-option observation

Broken
    reject direction/render for quality reasons, zero aesthetic label

Save move
    retain as a provisional direction, not yet a concept
```

## Learner

Start with an eight- or twelve-parameter preferred-target model in the current random coordinates. Do not immediately reuse the 44-parameter quadratic learner.

When the basis changes, the posterior must either:

- remain attached to the old basis instance;
- be transported through an explicit mapping with uncertainty;
- or restart while retaining immutable preference facts.

## From successful direction to concept

A selected random direction is a **provisional move**. Promotion to a reusable concept requires:

1. repeated positive support;
2. multiple anchors;
3. preferably multiple roots;
4. consistent visual-delta embeddings;
5. held-out recast success;
6. explicit model/basis/context scope.

A useful local move need not become a global semantic concept.

## Data model

```text
SoftBasisInstance
    basis_id
    model/prompt/config scope
    direction generator family
    direction vectors or digests
    calibration scales
    visual response receipts

SoftDirectionObservation
    basis_id
    coordinate/direction
    anchor and result
    root relation
    visual delta
    command outcome

RetainedDirection
    evidence
    validity context
    uncertainty
    status: provisional | retained | rejected | promoted
```

## Metrics

- rate of inert, broken, and duplicate directions;
- pairwise perceptual slate diversity;
- preference regret and time-to-first-liked candidate;
- held-out usefulness under another root;
- fraction of retained directions that remain useful after basis refresh;
- overlap with authored axes;
- user judgments of “hard to describe with a prompt”;
- concept-promotion precision.

## Baselines

- eight authored axes;
- random action points inside the authored chart;
- prompt-manifold PCA directions;
- isotropic random directions without calibration;
- fresh-seed-only search.

## Non-claims

A successful result would show that calibrated soft directions improve interactive discovery. It would not prove that:

- the directions are globally semantic;
- they are transferable across prompts or models;
- they correspond to human-nameable concepts;
- random embedding search replaces parent-conditioned evolution.
