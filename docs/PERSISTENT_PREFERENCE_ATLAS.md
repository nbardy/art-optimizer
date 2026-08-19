# Persistent Preference Atlas

**Status:** Normative v0 design for durable preference memory  
**Last updated:** 2026-08-20

## 1. Decision

Art Optimizer does **not** represent a user with one persistent embedding. It maintains and evolves a set of coherent preference components: a persistent **taste atlas**.

This is the load-bearing use of Ryan Murdock's generative-recommender idea in the product. Generated images re-enter the preference evidence stream, and the resulting preference representation is usable by generation. The v0 implementation is intentionally simpler than a sequence model or collaborative recommender, but its data contracts must admit those upgrades without changing interaction semantics.

The two learning timescales are:

```text
persistent preference atlas
    evolves across sessions, branches, and worlds

branch-local posterior
    adapts quickly over the next few selections and rerolls
```

The atlas persists. A world chooses a context-dependent mixture over it. A branch-local optimizer then learns a temporary residual goal.

## 2. Why one vector is insufficient

A user may separately prefer:

- dark architectural abstraction;
- organic particle systems;
- bright editorial illustration;
- surreal figurative painting;
- minimal geometric composition.

A single average embedding can land between these interests and describe none of them well. The system must preserve coherent modes, allow dormant modes to return, and deliberately distinguish:

1. exploration within one mode;
2. crossover between two modes;
3. exploration outside known modes.

## 3. Normative v0 representation

For user \(u\), the atlas snapshot is:

\[
\mathcal P_u
=
\left\{
P_k
\right\}_{k=1}^{K},
\qquad
P_k=
(\alpha_k,N_k,\mu_k,v_k,t_k,E_k,s_k).
\]

Each component stores:

- \(\alpha_k\): Dirichlet-style proposal mass;
- \(N_k\): weighted positive evidence mass;
- \(\mu_k\in\mathbb R^p\): mean in a versioned, whitened image-feature space;
- \(v_k\in\mathbb R_+^p\): diagonal variance with shrinkage and floors;
- \(t_k\): last activation time;
- \(E_k\): a bounded set of exemplar design IDs;
- \(s_k\): `active` or `dormant` status.

The normalized base mixture weight is:

\[
\pi_k=
\frac{\alpha_k}
{\alpha_{\mathrm{outside}}+\sum_j\alpha_j}.
\]

`outside` is not a learned aesthetic component. It reserves proposal probability for genuinely new regions so personalization cannot consume the entire search policy.

### 3.1 Feature space

The atlas does not store raw, timeless CLIP vectors. Each evidence image receives a versioned feature bundle, then a fixed projection produces the atlas vector:

\[
x=\operatorname{normalize}
\left(
W_{\phi}
[\phi_{\mathrm{semantic}};
 \phi_{\mathrm{style}};
 \phi_{\mathrm{composition}}]
\right).
\]

The projection and all source encoders have immutable revisions. A new feature-space revision creates a new atlas projection or an explicit migration; it never silently mixes incompatible vectors.

V0 may use a PCA-whitened Euclidean representation with diagonal covariance. A later implementation may use a spherical or learned density model behind the same snapshot contract.

## 4. Evidence is event-sourced

The atlas is a projection over typed, retractable evidence. Raw interaction events are never overwritten when weights or algorithms change.

```python
class PreferenceEvidence(BaseModel):
    evidence_id: str
    source_event_id: str
    user_id: str
    design_id: str
    feature_bundle_id: str
    feature_space_revision: str

    kind: Literal[
        "commit",
        "revisit",
        "favorite",
        "export",
    ]
    weight: float
    occurred_at: str
    active: bool
```

Unfavoriting deactivates the contribution created by the favorite event. It does **not** create a generic negative label and does not erase commit, revisit, or export evidence for the same design.

The projection can be rebuilt exactly from active evidence rows. This is preferable to applying irreversible negative sufficient-statistic updates.

### 4.1 Default positive evidence weights

Defaults are policy configuration, not universal constants:

| Evidence | Default weight | Interpretation |
|---|---:|---|
| Commit | 0.05 | promising local route; weak durable evidence |
| Revisit/restore | 0.25 | retained value after alternatives or time |
| Favorite | 1.00 | explicit membership in durable taste |
| Export | 1.50 | survived reflection and became an output |

Reroll and New world create no persistent update in v0. Hover creates none. Explicit durable dislike is deferred until a separate aversion model is specified.

## 5. Component assignment

Given evidence vector \(x\), component compatibility is computed with a shrinkage-stabilized diagonal Gaussian:

\[
\ell_k(x)
=
\log \pi_k
-
\frac12
\sum_{d=1}^{p}
\left[
\log(v_{kd}+\sigma_e^2)
+
\frac{(x_d-\mu_{kd})^2}
{v_{kd}+\sigma_e^2}
\right].
\]

Responsibilities are:

\[
r_k
=
\frac{\exp(\ell_k/T_r)}
{\sum_j\exp(\ell_j/T_r)}.
\]

`T_r`, the evidence-noise floor \(\sigma_e^2\), variance floors, and variance ceilings are versioned policy parameters.

### 5.1 Strong and weak evidence behave differently

A favorite or export may create a new component. A single exploratory commit may not.

- **Strong evidence:** favorite or export.
- **Weak evidence:** commit or revisit.

Strong evidence spawns a component when either:

\[
\max_k r_k < \tau_{\mathrm{responsibility}}
\]

or the nearest stabilized Mahalanobis distance exceeds \(\tau_{\mathrm{spawn}}\).

Weak evidence updates an existing compatible component only. Otherwise it enters a provisional buffer.

A provisional cluster is promoted only after at least three coherent weak events from distinct rounds or sessions. This prevents every exploratory click from becoming a permanent taste mode.

## 6. Weighted online updates

For evidence weight \(\omega\) and responsibility \(r_k\), define \(q=\omega r_k\). Maintain weighted sufficient statistics:

\[
N_k' = N_k+q,
\]

\[
\mu_k'
=
\mu_k+
\frac{q}{N_k'}(x-\mu_k),
\]

\[
M_{2,k}'
=
M_{2,k}
+
q(x-\mu_k)\odot(x-\mu_k').
\]

The diagonal covariance estimate is:

\[
v_k'
=
\operatorname{clip}
\left(
\frac{M_{2,k}'}{\max(N_k',\epsilon)}
+
\lambda_v v_0,
\,v_{\min},v_{\max}
\right).
\]

The proposal mass updates as:

\[
\alpha_k' = \alpha_k+q.
\]

The component's exemplars are updated by a bounded medoid/coverage policy rather than merely retaining the newest images. V0 keeps at most eight exemplars per component.

## 7. Component lifecycle

### 7.1 Dormancy, not deletion

Evidence mass does not decay away automatically. Proposal activation may decay with recency, but a dormant component remains recoverable.

A component becomes dormant when it has not been activated for a configured interval and is not currently relevant to the anchor. Dormancy affects proposal probability, not historical truth.

### 7.2 Merge

An offline maintenance job may propose a merge when components have low symmetric divergence, overlapping exemplars, and compatible generation recipes. V0 requires the merge to be logged and reversible.

Once preference modes become user-visible or user-named, automatic merge is prohibited without confirmation.

### 7.3 Split

Automatic split is deferred. V0 can flag a component for review when its covariance becomes broad or its evidence is visibly multimodal, but it should not perform opaque online splitting.

### 7.4 Delete

Components are deleted only through explicit user data deletion or complete evidence retraction. They are never deleted simply for being old.

## 8. Context-dependent activation

The atlas is not mixed with the same weights in every world. For anchor image \(I_t\), conditions \(c_t\), and branch history \(h_t\), the world/branch relevance is:

\[
q_k
\propto
\exp\left[
\log\pi_k
+
\eta_a\,\operatorname{sim}(\mu_k,\phi(I_t))
+
\eta_c\,g_k(c_t)
+
\eta_r\,R_k(t)
\right].
\]

Where:

- anchor similarity favors modes compatible with the current image;
- \(g_k(c_t)\) is optional condition relevance;
- \(R_k(t)\) is bounded recency activation;
- a fixed outside-prior mass remains available.

This relevance vector is stored in an immutable `WorldPreferenceContext` or `BranchPreferenceContext` snapshot.

## 9. How the atlas affects generation in v0

The atlas is a proposal source, not a magic scalar added to every unseen candidate.

Before a learned action-to-image surrogate exists, the system cannot honestly evaluate

\[
m_u(G(s,a))
\]

without rendering \(G(s,a)\). V0 therefore integrates persistent taste through explicit proposal policies:

1. retrieve one or more relevant atlas components;
2. select representative exemplars;
3. compile bounded exemplar guidance through the renderer capability interface;
4. allocate a candidate slot to that guided proposal;
5. record the component IDs, exemplar IDs, guidance strength, and proposal probability.

Preferred compilation order:

1. multi-reference or reference-attention guidance;
2. a compatible, previously learned control recipe under the same renderer/control-basis revision;
3. oversample-and-rerank after low-resolution rendering;
4. typed refusal and fallback to controlled surprise.

The adapter must not silently pretend a component was used when no supported guidance path exists.

### 9.1 First round in a new world

When an atlas exists, the first quartet should contain:

1. a neutral continuation from the new stochastic root;
2. guidance from the most context-relevant preference component;
3. guidance from a distinct secondary or dormant component;
4. an outside-prior surprise proposal.

After branch-local evidence accumulates, only one slot normally comes directly from the atlas. The other slots are governed by the local optimizer.

### 9.2 Within, crossover, and outside proposals

- **Within-prior:** one component guides the proposal.
- **Crossover:** two compatible components guide a proposal with explicit bounded weights.
- **Outside-prior:** no component guidance; optimize novelty subject to quality and safety constraints.

Crossover is never implemented by blindly averaging all component means.

## 10. Relationship to the branch-local posterior

The branch-local posterior and atlas are distinct models with distinct evidence.

```text
atlas
    says which durable taste regions may be relevant

local posterior
    says which absolute control coordinates are improving this branch now
```

V0 combines them at the proposal-policy level. It does **not** initialize the local utility weight vector from an unvalidated projection of image-embedding means into generator action space.

A later learned transport model may provide:

\[
p(w_{\mathrm{branch}}\mid \mathcal P_u,I_t,c_t),
\]

but that is an evaluated upgrade, not an implicit assumption in the first implementation.

## 11. Branch selection and atlas updates

A candidate commit immediately updates the branch-local model. Its persistent contribution is intentionally small.

A favorite or export updates the atlas strongly even if the design was reached through an unusual or short-lived branch.

A history restore activates the component(s) that explain the restored design and adds moderate evidence because the design retained value after intervening alternatives.

Repeated rerolls remain local. They do not lower an atlas component's weight merely because one proposal policy produced four poor descendants.

## 12. Snapshot contracts

```python
class PreferenceComponent(BaseModel):
    component_id: str
    feature_space_revision: str

    mean: tuple[float, ...]
    variance_diagonal: tuple[float, ...]
    evidence_mass: float
    proposal_mass: float

    last_activated_at: str
    status: Literal["active", "dormant"]
    exemplar_design_ids: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]

class PersistentPreferenceSnapshot(BaseModel):
    snapshot_id: str
    user_id: str
    schema_version: Literal["persistent-atlas/v0"]
    policy_revision: str
    feature_space_revision: str
    components: tuple[PreferenceComponent, ...]
    outside_prior_mass: float
    created_at: str

class BranchPreferenceContext(BaseModel):
    context_id: str
    snapshot_id: str
    anchor_design_id: str
    component_responsibilities: dict[str, float]
    selected_component_ids: tuple[str, ...]
    policy_revision: str
```

Every candidate proposed from a component records the atlas snapshot and branch-context IDs used.

## 13. Privacy and user control

The atlas is sensitive personal data. V0 requires:

- private-by-default storage;
- export of components, exemplars, and supporting events;
- deletion and complete projection rebuild;
- clear retraction when a favorite is removed;
- no cross-user collaborative use without separate consent;
- no shared-weight or adapter training from private evidence by default.

## 14. Tests

At minimum:

1. one strong outlier favorite spawns a component;
2. one outlier commit does not;
3. three coherent weak events can promote a provisional component;
4. updates are order-stable within numeric tolerance;
5. unstar retracts only the favorite contribution;
6. components become dormant without losing evidence;
7. new world preserves the atlas snapshot lineage;
8. reroll does not mutate the atlas;
9. outside-prior mass remains nonzero;
10. incompatible feature revisions cannot be mixed;
11. proposal records identify the component and exemplar actually used;
12. rebuilding from active evidence reproduces the snapshot.

## 15. Deferred upgrades

- Murdock-style collaborative filtering across consenting users;
- sequence-conditioned Preference Prior models;
- nonparametric mixture models;
- explicit persistent aversion components;
- learned transport from image preference modes to action-space priors;
- user-visible naming, pinning, merging, and splitting of taste modes;
- offline LoRA/DPO consolidation.

These upgrades should replace atlas internals or add proposal sources without changing the meaning of commit, reroll, favorite, restore, or New world.
