# V0 Algorithm Specification

**Status:** Normative implementation contract  
**Last updated:** 2026-08-20

This document removes the remaining “Bayesian linear **or** GP,” “fixed **or** varied noise,” and “prior score **or** proposal source” ambiguity from the first implementation.

`STATE_AND_CONTROL_CONTRACT.md` governs the identity of worlds, design states, branch nodes, and control coordinates. Where this document conflicts with exploratory language in `RESEARCH_NOTES.md`, `ARCHITECTURE.md`, or `CODE_DESIGN.md`, this document governs v0 algorithm behavior.

## 1. V0 objective

Implement a reproducible, online optimizer over one bounded world-level control vector. At every round, the system presents four descendants of the current design. The user either commits one or rerolls, which means the current design wins against the exposed candidates.

V0 must prove:

1. the interaction semantics are correct;
2. the control space is replayable and sufficiently smooth;
3. a lightweight preference posterior outperforms random search;
4. persistent preference modes improve cold starts without collapsing novelty.

It does not attempt long-horizon reinforcement learning, per-click model training, or universal semantic directions.

## 2. World-level parameterization

Each world has one immutable renderer/control-basis manifest and one bounded **absolute** action vector:

$$
a\in\mathcal A\subset[-1,1]^d,
\qquad d\le16\text{ in v0}.
$$

The current committed design has coordinates \(a_t\). A candidate is another absolute point \(a_{tj}\), usually inside a trust region around \(a_t\).

A renderer compiles:

$$
I(a)=G_\theta(m,z_0,c,r,q,B,a),
$$

where:

- \(m\): exact model/runtime manifest;
- \(z_0\): materialized world root noise;
- \(c\): base text/structural conditions;
- \(r\): fixed world reference identities, including any atlas slots;
- \(q\): output constraints and preservation locks;
- \(B\): versioned control-basis manifest;
- \(a\): absolute world coordinates.

The absolute-coordinate requirement is important: observations from several rounds remain comparable in one parameterized design space. A parent-relative editing adapter that cannot compile an absolute world coordinate is outside the normative v0 optimizer and must use a separate experimental policy.

Each `DesignState` stores:

- `absolute_action = a_t`;
- `parent_delta = a_t-a_parent`.

Local posterior and trust-region snapshots belong to the committed `BranchNode`, not the immutable `DesignState`.

## 3. Control-basis gate

The real renderer is not accepted merely because it produces images. Before optimization, its basis must pass an empirical gate.

For each coordinate and several anchors, test finite sweeps at fixed other coordinates. The basis is accepted when:

1. all coordinates are bounded and replayable;
2. small coefficient changes usually produce nonzero but non-catastrophic perceptual change;
3. sibling renders do not collapse into duplicates at the default radius;
4. at least eight coordinates produce distinguishable variation;
5. unsupported controls return a typed refusal;
6. latency and memory meet the recorded target profile.

V0 may begin with fewer than sixteen dimensions. It should not pad the space with meaningless controls.

## 4. Noise policy

### 4.1 Integer seeds are provenance only

The PRNG seed is stored, but no optimizer arithmetic is performed on seed integers.

### 4.2 Default

The first real-optimizer experiment sets noise-control dimension to zero. All candidates in a world use the same materialized root noise while semantic/reference/adapter controls are validated.

Noise directions are enabled only after the control-basis and replay gates pass.

### 4.3 Optional tangent-space noise coordinates

For isotropic Gaussian initial noise, a linear offset can leave the typical set as its norm grows. Use a tangent basis and a spherical map instead.

Let:

$$
r=\lVert z_0\rVert,
\qquad
\hat z_0=z_0/r,
$$

and choose:

$$
B_z^TB_z=I,
\qquad
B_z^T\hat z_0=0.
$$

For noise coefficients \(v\in\mathbb R^{d_z}\), define:

$$
z(v)=
\begin{cases}
z_0,&\lVert v\rVert=0,\\
r\left[
\cos(\lVert v\rVert)\hat z_0
+
\sin(\lVert v\rVert)
B_z\dfrac{v}{\lVert v\rVert}
\right],&\text{otherwise.}
\end{cases}
$$

This preserves the root-noise norm. The basis and coefficients are world-local and never assumed to transfer to another root.

The renderer declares whether this geometry is valid for its noise distribution. Otherwise it refuses the noise-control block.

## 5. Choice semantics

The current committed design is the outside option. This removes the need for an unidentified free acceptance threshold in v0.

For round \(t\):

- anchor action: \(a_t\);
- exposed candidate set: \(E_t\subseteq\{1,2,3,4\}\);
- selected outcome: \(y_t\in E_t\cup\{0\}\);
- \(y_t=0\) means reroll/current anchor wins.

Candidates that failed, never rendered, or were not meaningfully exposed are excluded.

A candidate is meaningfully exposed when:

- a valid preview was ready;
- at least 50% of the candidate card was visible;
- it was visible for at least 300 ms;
- or it was explicitly previewed, favorited, or selected.

A reroll with fewer than two meaningfully exposed candidates becomes `RoundSkipped` and has no preference weight.

## 6. Local utility model

### 6.1 Feature map

V0 uses a Bayesian linear utility model over a fixed quadratic feature map of absolute action coordinates.

For \(d\le16\):

$$
\psi(a)=
[
 a_1,\ldots,a_d,
 a_1^2,\ldots,a_d^2,
 \{a_i a_j\}_{i<j}
].
$$

No intercept is required because choices use utility differences.

The scalar latent utility is:

$$
f(a)=w^T\psi(a),
$$

with prior:

$$
w\sim\mathcal N(0,\lambda^{-1}I).
$$

All action coordinates and feature-map revisions are stored in the preference snapshot.

### 6.2 Anchor-relative utility

For candidate \(j\):

$$
\Delta\psi_{tj}=\psi(a_{tj})-\psi(a_t),
$$

$$
\Delta f_{tj}=w^T\Delta\psi_{tj}.
$$

The anchor has \(\Delta f_{t0}=0\).

### 6.3 Multinomial-choice likelihood

For a selected candidate \(j\in E_t\):

$$
P(y_t=j\mid w)
=
\frac{\exp(\Delta f_{tj}/\tau)}
{1+\sum_{k\in E_t}\exp(\Delta f_{tk}/\tau)}.
$$

For reroll:

$$
P(y_t=0\mid w)
=
\frac{1}
{1+\sum_{k\in E_t}\exp(\Delta f_{tk}/\tau)}.
$$

This is one typed choice observation, not three independent pairwise labels.

### 6.4 Observation weights and drift

Default weights:

- candidate commit: \(\omega_t=1.0\);
- soft reroll: \(\omega_t=0.35\);
- explicit `dislike all`, if later exposed: \(\omega_t=1.0\).

Apply exponential branch recency:

$$
\tilde\omega_t
=
\omega_t\gamma^{T-t},
\qquad
\gamma=0.97\text{ by default}.
$$

The values are versioned policy defaults and must be benchmarked, but v0 has one configured set rather than per-engineer interpretation.

## 7. Posterior update

V0 uses a Laplace approximation.

For branch observations \(\mathcal D\), maximize:

$$
\mathcal L(w)
=
-\frac{\lambda}{2}w^Tw
+
\sum_{t\in\mathcal D}
\tilde\omega_t
\log P(y_t\mid w).
$$

Use damped Newton/IRLS with:

- warm start from the inherited branch snapshot mode;
- maximum 10 iterations;
- backtracking line search;
- Hessian jitter \(\epsilon I\);
- convergence by relative objective and step norm;
- failure fallback to the previous valid snapshot.

The approximate posterior is:

$$
q(w)=\mathcal N(\hat w,\Sigma_w),
\qquad
\Sigma_w=
[-\nabla^2\mathcal L(\hat w)]^{-1}.
$$

Snapshots are immutable. A round uses only a snapshot completed before that round was proposed.

### 7.1 Branch inheritance

Every committed `BranchNode` points to the local-posterior snapshot associated with its ancestral observation path.

Restoring an old branch node restores that snapshot. New descendants inherit observations along that path only; they do not inherit contradictory observations from sibling branches.

New world initializes a fresh zero-mean local posterior. The persistent atlas influences fixed world coordinates and proposal roles, not the v0 local weight prior.

## 8. Predictive mean and uncertainty

For proposed action \(a\) relative to anchor \(a_t\):

$$
\Delta\psi(a)=\psi(a)-\psi(a_t),
$$

$$
\mu(a)=\hat w^T\Delta\psi(a),
$$

$$
\sigma^2(a)=
\Delta\psi(a)^T
\Sigma_w
\Delta\psi(a).
$$

These are latent utility-improvement moments, not calibrated probabilities of artistic satisfaction.

## 9. Trust region

Search is bounded around the current action:

$$
\mathcal T_t
=
\{a\in\mathcal A:\lVert D^{-1}(a-a_t)\rVert_2\le r_t\},
$$

where \(D\) contains per-coordinate scale factors from the control-basis manifest.

Default normalized settings:

```text
initial radius                 0.60
minimum radius                 0.08
maximum radius                 1.50
soft-reroll multiplier         1.35
refinement multiplier          0.85
commits before refinement      2
```

Behavior:

- commit moves the center to the selected absolute action;
- after two consecutive commits, shrink radius by `0.85` and reset the success counter;
- soft reroll expands by `1.35`, resets the success counter, and raises exploration pressure;
- restore reloads the search snapshot stored on the branch node;
- New world resets to the initial radius.

The user never silently crosses into a new stochastic world because of trust-region expansion.

## 10. Candidate pool

For each round, generate a deterministic hidden action pool using the planner RNG recorded in the round manifest:

1. 192 scrambled Sobol proposals in the trust region;
2. 64 Gaussian proposals centered on \(a_t\), clipped to bounds;
3. axis probes along the largest posterior-variance eigendirections when available;
4. proposals emphasizing any fixed atlas reference-weight coordinates installed in the world basis.

Remove candidates that:

- violate action bounds or renderer capabilities;
- are within `epsilon_action` of the anchor;
- duplicate another action under scaled distance;
- fail preservation-lock preflight.

V0 optimizes this finite pool. It does not require fragile continuous acquisition-function optimization.

No candidate may change the world's fixed prompt, reference identities, adapter identities, or control basis.

## 11. Four proposal roles

### Slot 1 — best local continuation

Choose:

$$
a_1=\arg\max_{a\in\mathcal C}\mu(a).
$$

### Slot 2 — diverse posterior sample

Draw:

$$
\tilde w\sim\mathcal N(\hat w,\Sigma_w),
$$

then maximize sampled improvement subject to minimum scaled distance from slot 1:

$$
a_2
=
\arg\max
\tilde w^T\Delta\psi(a).
$$

### Slot 3 — informative probe

Choose the highest predictive variance subject to distance from slots 1 and 2:

$$
a_3=\arg\max\sigma^2(a).
$$

This is an inexpensive uncertainty proxy; exact expected information gain is deferred.

### Slot 4 — persistent mode or controlled surprise

If the world control basis contains atlas reference-weight coordinates, choose a distinct proposal that exercises the most relevant underexplored installed component or a bounded crossover between two installed components.

Otherwise choose a controlled-surprise point maximizing:

$$
\mu(a)+\beta_s\sigma(a)+\lambda_s d(a,a_t),
$$

subject to a maximum jump and preservation constraints.

The role, fixed atlas coordinate IDs, component IDs, and fallback reason are stored. The UI need not label slots by role.

### 11.1 First round special case

With no branch observations:

1. neutral low-distance proposal;
2. increased weight on the most relevant installed atlas component;
3. increased weight on a distinct secondary/dormant installed component or broad control probe;
4. outside-prior surprise.

If the atlas is empty or the renderer installed no atlas slots, use four deterministic, well-separated basis probes.

## 12. Perceptual duplicate handling

Action-space diversity is only a proxy. When preview embeddings become available, compute pairwise perceptual distance.

If two candidates are below `epsilon_image`:

- retain the higher-priority role;
- request a replacement for the duplicate slot;
- do not move already exposed content between slots;
- exclude the replaced candidate from the eventual choice set unless it was meaningfully exposed.

A round may still proceed if replacement would add unacceptable latency.

## 13. Reroll

A preference-bearing soft reroll means the anchor was selected over the meaningfully exposed candidates.

It:

1. appends one outside-option observation;
2. keeps the committed design, world root, and absolute action;
3. expands the trust region;
4. increases exploration coefficient;
5. creates a new round and planner seed;
6. does not mutate the persistent atlas.

A third consecutive reroll may enable one explicit tangent-noise proposal if that capability has passed its gate. It still does not replace the world root.

## 14. Commit

A commit:

1. validates that the candidate belongs to the active round;
2. records the exposed choice set plus anchor;
3. atomically creates a new `BranchNode` pointing to the candidate's immutable `DesignState`;
4. advances the current branch pointer;
5. queues the local-posterior update from the typed observation;
6. adds weak commit evidence to the persistent-atlas event stream;
7. generates the next round from the selected absolute action using the latest completed branch snapshot available.

The learner update never mutates the selected `DesignState`. When it completes, its snapshot is attached to the branch-node projection and is used only by later rounds that record that snapshot ID.

## 15. New world

New world:

1. retains prompt intent, output settings, favorites, and the persistent atlas by default;
2. computes a context-dependent atlas mixture;
3. selects zero, one, or two fixed atlas exemplars for supported world reference slots;
4. constructs an immutable control-basis manifest;
5. draws and materializes independent root noise;
6. resets branch observations and trust-region state;
7. creates a neutral root `DesignState` and root `BranchNode`;
8. varies declared world coordinates in the first quartet.

This preserves a clean distinction between stochastic-world reset, world basis construction, and branch-local preference learning.

## 16. Persistent-atlas integration

V0 does not add a persistent image score to unseen actions unless a validated action-to-image surrogate exists.

Instead, the atlas participates at world creation by installing fixed exemplar-reference coordinates and later through proposal roles that vary those declared coordinates, as specified in `PERSISTENT_PREFERENCE_ATLAS.md` and `STATE_AND_CONTROL_CONTRACT.md`.

This avoids pretending that image-space preference components can be projected into generator action coordinates without learned transport, and avoids presenting candidates with hidden incompatible conditions.

## 17. Planner pseudocode

```python
def propose_round(branch, local_snapshot, world_context, renderer, rng):
    pool = sample_trust_region(
        center=branch.current_absolute_action,
        radius=branch.search.radius,
        sobol_count=192,
        gaussian_count=64,
        rng=rng,
    )
    pool += posterior_axis_probes(local_snapshot, branch.search)
    pool += atlas_coordinate_probes(world_context, branch, rng)

    pool = renderer.preflight_absolute_actions(branch.world_id, pool)
    pool = dedupe_actions(pool)

    posterior = predict_improvement(
        local_snapshot,
        anchor=branch.current_absolute_action,
        actions=pool,
    )

    first = highest_mean(pool, posterior)
    second = thompson_diverse(pool, posterior, first, rng)
    third = highest_variance(pool, posterior, [first, second])
    fourth = atlas_or_surprise(
        pool,
        posterior,
        world_context,
        [first, second, third],
        rng,
    )

    return CandidateRound(
        parent_branch_node_id=branch.branch_node_id,
        parent_design_id=branch.design_id,
        proposals=[first, second, third, fourth],
        local_snapshot_id=local_snapshot.snapshot_id,
        world_preference_context_id=world_context.context_id,
        planner_rng_state=serialize_rng(rng),
    )
```

## 18. Simulated-user baselines

The optimizer is not accepted without comparison against:

1. uniform random proposals;
2. Gaussian random walk around the anchor;
3. top-four posterior mean without role diversity;
4. independent-seed browsing;
5. no-persistent-atlas cold start.

Simulated utility families must include:

- linear preferences;
- nonlinear quadratic preferences;
- multimodal preferences;
- drifting local goals;
- noisy and inconsistent choices;
- a user who frequently chooses the anchor/reroll.

## 19. Normative tests

1. anchor is present as the outside option in every preference observation;
2. hidden or failed candidates never enter a choice set;
3. one selection produces one multinomial observation;
4. soft reroll has the configured lower weight;
5. posterior snapshots are deterministic under fixed inputs and RNG;
6. restoring a branch node restores its ancestral local snapshot;
7. sibling-branch observations do not leak into one another;
8. proposal roles are distinct under action-space distance constraints;
9. outside-prior proposals remain possible;
10. integer seed adjacency is never used;
11. optional noise movement preserves norm within tolerance;
12. renderer refusal cannot be silently converted into a zero action;
13. New world resets local state but preserves atlas lineage;
14. every atlas-guided action references fixed world coordinates;
15. candidate-specific hidden reference identities are rejected;
16. all planner randomness is replayable from the round manifest.

## 20. What remains empirical

The following are not missing mathematical definitions; they are experiments that determine whether the product works:

- which real model exposes the best smooth, bounded control basis;
- which basis dimensions are useful enough to retain;
- whether fixed root noise becomes visually repetitive;
- whether the default trust-region constants are appropriate;
- whether the quadratic utility model is sufficient;
- whether fixed atlas-reference coordinates improve first-round choices;
- whether corner previews provide enough information at target sizes;
- whether low-resolution choices agree with final-render choices.

Failure of an experiment should replace a versioned component, not reopen the meaning of the interaction events.
