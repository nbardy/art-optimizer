# One Authoritative Taste State

**Status:** independent architecture review and Round 2 decision proposal
**Date:** 2026-08-22
**Scope:** preference evidence, taste memory, multimodality, concepts, candidate policy, and the relationship to Shimizu, evolutionary search, and reinforcement learning
**Builds on:** [Round 1 root-cause review](11_ROUND_1_ROOT_CAUSE_REVIEW.md) and [five mathematical partial solutions](12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md)

## Executive judgment

The disjoint learner finding is concerning, but it is not evidence that the whole project was misguided.

The current implementation has three different objects that can all answer the question “what does this user like?”:

| Current object | Representation | Update source | What it controls |
|---|---|---|---|
| branch posterior | 44 quadratic coefficients over an eight-dimensional action vector | exposed slate choice or anchor win | next-round planner |
| persistent atlas | clusters of 13 image statistics plus action centroids | commit, revisit, and favorite are wired; an export weight exists but has no current service path | New World initialization |
| browser Concept Library | clusters of accepted normalized action deltas | browser-observed commits and rerolls | lane labels and Recast |

They do not update one another, do not share evidence semantics, and cannot be replayed as one belief. The UI makes them sound like different views of one learned taste. They are not.

The correction should be decisive:

> Art Optimizer should have one immutable preference-event history and one server-side, versioned `TasteState` projection containing homogeneous, representation-scoped taste families. Every UI, planner, branch, and New World operation should read that state. No other component may learn an independent definition of taste.

The family idea is directionally right, but its mathematical category in v1 is a finite Bayesian collection with explicit branch activation; a later treatment may infer a latent mixture. It is not a genetic algorithm. Shimizu used separately editable GP subjective functions plus guided sampling; he did not evolve tastes or add RL.

“One learning system” should not mean one monolith. Evidence, belief, proposal policy, rendering, and UI remain separate primitives. It means there is exactly one source of preference truth.

## What we got wrong

The deepest error was not Bayesian inference, clustering, or local storage individually. It was allowing three approximations to acquire the same ontology.

```text
branch posterior says
    taste = utility over actions in this branch

atlas says
    taste = cluster of preferred image summaries across sessions

Concept Shelf says
    taste = additive collection of accepted movement directions
```

Those definitions are not interchangeable:

- a utility surface ranks alternatives;
- a cluster represents a region or mode;
- an additive direction represents a composable factor.

The implementation never supplied a mathematical map among them. Consequently a click can change all three in different ways, a reroll can create two different kinds of negative evidence, and switching UI routes can preserve state whose meaning the new UI did not choose.

The prior synthesis explicitly proposed “persistent preference representation + fast branch-local preference learning.” Round 1 shows that this decomposition is too permissive unless both are revisions or timescales inside one canonical state. As an architecture recommendation, that earlier decomposition is superseded by this review.

## What we did well

The project has unusually good substrate for the correction:

- a click is already modeled as one multinomial choice over the exposed slate, not four independent labels;
- the current image is an explicit outside option;
- exposure qualification avoids learning from unseen candidates;
- design IDs/artifacts are treated as immutable by service transitions, while branch IDs, mutation versions, and command IDs make exact event semantics possible;
- the fixed-seed world is a defensible controlled-comparison treatment;
- renderer, codec, planner, learner, and storage boundaries are modular;
- the research documents explicitly left the control basis unvalidated instead of claiming success.

So the scientific baseline was useful. The mistake was promoting research proxies into product nouns before the representation gates passed.

## The ontology that must remain separate

Unification starts by refusing several tempting collapses.

| Object | Meaning | May learn taste? |
|---|---|---|
| `PreferenceEvent` | immutable fact about what was shown and what the user did | no |
| `TasteFamily` | current probabilistic belief derived from events | **yes; sole authority** |
| taste component | one alternative preference region or mode | part of `TasteFamily` |
| active taste | mode currently being refined on a branch | pointer inside `TasteFamily` |
| attribute | composable causal factor such as “more translucent” | not in v1 |
| candidate | a rendered proposal | no |
| planner | policy that chooses which candidates to test | no |
| renderer/control codec | map from generation state and action to pixels | no |
| UI | projection plus typed commands | no |

This gives one learner without pretending the renderer is a learner or the planner is a taste.

## The user's recurrence, made exact

The proposed intuition is right:

\[
F(\text{old taste},\text{history},\text{new vote})
\longrightarrow
\text{new taste}.
\]

The safe event-sourced form is slightly different. Let the immutable history after event \(t\) be:

\[
H_t=H_{t-1}\mathbin{\|}e_t.
\]

For reducer revision \(r\), the authoritative projection is:

\[
S_t=\operatorname{Fold}_r(S_0,H_t).
\]

Its incremental equivalent is:

\[
S_t=F_r(S_{t-1},e_t).
\]

The output is a new revision of the whole family state. It does not imply that every vote spawns a new taste component.

Do not pass the previous posterior and the complete old history into an updater that consumes both. The old posterior already summarizes that history; consuming it again double-counts evidence.

### Replay equivalence

If `Fold` is defined by repeated application of deterministic `F`, then:

\[
\operatorname{Fold}_r(S_0,H_t\mathbin{\|}e_{t+1})
=F_r(\operatorname{Fold}_r(S_0,H_t),e_{t+1}).
\]

This follows directly from the recursive definition of a fold. It is the invariant that lets an online snapshot be fast while the raw history remains auditable and rebuildable.

The v1 component fit should use the complete assigned evidence set and one fixed base prior. Incremental processing may warm-start the optimizer, but must refit the joint MAP instead of treating yesterday's Laplace approximation as today's prior. Because the objective below is strictly concave, the component posterior approximation is a deterministic function of its evidence set and model revision rather than an artifact of update order.

The reducer revision, numerical settings, and representation scope must be stored. Otherwise “replay” silently changes when code or a control bank changes.

## One lean taste component

Start with the smallest model that has an interpretable geometric meaning.

For a fixed, validated \(d\)-dimensional control basis, taste component \(k\) has an ideal point:

\[
\theta_k\in\mathbb R^d,
\]

a fixed positive-definite action metric and utility-curvature matrix:

\[
Q\succ0,
\]

and choice temperature \(\tau>0\). Define utility:

\[
u_k(a)
=-\frac{1}{2}(a-\theta_k)^TQ(a-\theta_k).
\]

For exposed alternatives \(A=\{a_0,\ldots,a_m\}\), including the current anchor \(a_0\), use the multinomial-choice likelihood:

\[
P(y=j\mid A,\theta_k)
=
\frac{\exp(u_k(a_j)/\tau)}
{\sum_{\ell=0}^{m}\exp(u_k(a_\ell)/\tau)}.
\]

This says one simple thing: this taste tends to choose actions nearer its currently inferred preferred region, while allowing noisy choices.

### Why this is only eight unknowns

Expand the utility:

\[
u_k(a)
=a^TQ\theta_k-\frac{1}{2}a^TQa-\frac{1}{2}\theta_k^TQ\theta_k.
\]

The last term is common to every alternative and cancels inside a softmax. Once \(Q\) and \(\tau\) are fixed, the slate logits are affine in the eight entries of \(\theta_k\).

The current quadratic feature model has:

\[
d+d+\frac{d(d-1)}2
=\frac{d^2+3d}{2}
\]

unknowns. At \(d=8\), that is 44. The ideal-point component has eight.

This is a deliberate bias. It assumes one taste component is one basin with a preferred center. If held-out choices falsify that assumption, the next escalation is a nonlinear component model such as a preference GP—not 44 weakly identified coefficients by default.

## Posterior refit and uniqueness

Give component \(k\) one fixed, materialized Gaussian base prior:

\[
\theta_k\sim\mathcal N(m_0,C_0).
\]

For evidence event \(e\), alternative \(j\), and weight \(\omega_e>0\), define:

\[
\ell_{e,j}
=
\frac{a_{e,j}^TQ\theta-\frac{1}{2}a_{e,j}^TQa_{e,j}}{\tau}.
\]

If \(E_k\) is the complete set of events assigned to the component, its joint log posterior, up to a constant, is:

\[
L_{E_k}(\theta)
=-\frac{1}{2}(\theta-m_0)^TC_0^{-1}(\theta-m_0)
+\sum_{e\in E_k}\omega_e
\left[\ell_{e,y_e}-\log\sum_j e^{\ell_{e,j}}\right].
\]

Let \(p_{e,j}\) be the event's current softmax probability and:

\[
\bar a_e=\sum_jp_{e,j}a_{e,j}.
\]

Then:

\[
\nabla L_{E_k}
=-C_0^{-1}(\theta-m_0)
+\sum_{e\in E_k}\frac{\omega_e}{\tau}Q(a_{e,y_e}-\bar a_e),
\]

and:

\[
\nabla^2L_{E_k}
=-C_0^{-1}
-\sum_{e\in E_k}\frac{\omega_e}{\tau^2}
Q\operatorname{Cov}_{p_e}(a_e)Q.
\]

Because \(C_0^{-1}\succ0\) and every \(\operatorname{Cov}_{p_e}(a_e)\succeq0\), the Hessian is strictly negative definite. Therefore every evidence set has one unique MAP. The joint Laplace covariance is:

\[
C_{E_k}
=\left[
C_0^{-1}
+\sum_{e\in E_k}\frac{\omega_e}{\tau^2}
Q\operatorname{Cov}_{p_e}(a_e)Q
\right]^{-1}
\]

evaluated at that MAP.

On every new event, refit this objective over the complete assigned history, using the previous MAP only as a numerical warm start. This is cheap at eight dimensions, makes retraction/split/merge semantics clean, and avoids silently counting a Laplace approximation as a new prior.

The likelihood preserves the strongest part of the existing learner: every term uses the entire exposed slate. It does not pretend that the chosen action is an unbiased sample from a taste distribution.

## Information and identifiability

Pairwise log odds inside a slate satisfy:

\[
\tau\log\frac{P_j}{P_\ell}
=(a_j-a_\ell)^TQ\theta
-\frac12(a_j^TQa_j-a_\ell^TQa_\ell).
\]

With fixed invertible \(Q\), the target \(\theta\) is identifiable only when accumulated exposed action differences span \(\mathbb R^d\). Repeatedly probing the same few directions cannot identify the remaining coordinates, regardless of click count.

For a slate with \(m+1\) alternatives, \(\operatorname{Cov}_p(a)\) has rank at most \(m\). A current five-way comparison therefore contributes Fisher rank at most four.

Consequently:

- an eight-parameter component needs at least two geometrically independent five-way rounds before the data information can be full rank;
- the current 44-parameter component needs at least eleven.

These are necessary lower bounds, not promises of useful learning after two or eleven clicks. The prior makes the posterior numerically invertible from round one; it does not manufacture data information.

Also fix \(Q\) and \(\tau\) in the primitive experiment. Scaling both by the same constant leaves the choice probabilities unchanged, so they are not jointly identified by choices without an additional convention.

## The family state

For one compatible representation scope, the canonical state is a finite family:

\[
\mathcal B_t
=
\left(
\{T_{t,k}\}_{k=1}^{K_t},
Z_t,
r,
c_t
\right),
\]

where:

- \(T_{t,k}\) is one component posterior, evidence set, exemplars, status, and lineage;
- \(Z_t\) maps every live branch to an active component and immutable component revision;
- \(r\) is the reducer/model revision;
- \(c_t\) is the last consumed event cursor.

For an observation on branch \(b_t\), v1 updates exactly that branch's active component:

\[
r_{t,k}=\mathbf 1[k=Z_t(b_t).\operatorname{component\_id}].
\]

That is intentionally simpler and more auditable than inferring a latent component assignment from every click. A later mixture experiment may compute soft responsibilities:

\[
r_{t,k}
=
\frac{\pi_{t-1,k}m_{t,k}}
{\sum_{j=0}^{K_t}\pi_{t-1,j}m_{t,j}},
\]

where \((\pi_{t-1,0},\ldots,\pi_{t-1,K_t})\) is one normalized nonnegative prior over the new-component hypothesis and existing components, \(m_{t,k}\) is component \(k\)'s posterior-predictive probability for the observed choice, and \(r_{t,0}\) is the resulting new-component responsibility. That is a later treatment, not the v1 default; v1 stores no hidden heuristic component salience.

For Gaussian \(q_k(\theta)\), that posterior-predictive probability is the logistic-normal integral:

\[
m_{t,k}
=
\int P(y_t\mid A_t,\theta)q_k(\theta)\,d\theta.
\]

It is not generally equal to the softmax evaluated at the posterior mean. Calibration, prequential scoring, and any later soft assignment must name a deterministic approximation revision, such as seeded quasi-Monte Carlo. A plug-in MAP score may be used for a fast heuristic only if it is labeled as such.

One active mode per branch does not erase multimodality. It makes the current modeling assumption visible and correctable.

At user level, one authoritative `TasteState` maps exact `scope_id` values to homogeneous families and retains an immutable revision DAG plus branch-head pointers. The event stream remains linear; events can name an older base revision and create a sibling head without erasing later revisions. This is one reducer and one preference authority, not permission to pool coordinates across prompt-conditioned direction banks.

## Lifecycle operations

The operations need precise meanings.

### Modify

A qualified `PreferenceChoice` updates the active component with the choice likelihood above. This is the ordinary path.

### Switch

Change the branch's active `taste_id`. Switching supplies no preference evidence and rewrites no history.

### Spawn

Create a provisional component from a broad prior centered near an explicitly selected design, then make it the branch's active pointer. “Provisional” is lifecycle status; “active” only describes the branch pointer. In v1, spawning is an explicit user command or a system suggestion requiring confirmation.

A single surprising vote must not automatically spawn a taste. That vote could mean label noise, a poor slate, a changed local goal, a rendering artifact, a weak control direction, or genuinely new taste. The observable click alone does not identify which explanation is true.

### Fork

`TasteFork` creates a new provisional taste identity that shares immutable evidence ancestry so the user can explore reversibly. It becomes durable only after explicit promotion or sufficient independent evidence. `BranchForkFromCheckpoint` instead creates a navigation head pointing to the same historical taste identity and revision; it makes no new-taste claim.

### Split

Partition the parent's evidence IDs into two disjoint sets and refit both children from the same declared prior. Archive the parent revision but retain it in lineage.

Do not split posterior coordinates and do not halve a mean vector. A split is a claim about two groups of observations and two alternative child modes, not two fractions or composable attributes of one parameter vector.

### Merge

Union and deduplicate the two evidence sets, choose the compatible or explicitly declared merge prior, then refit one child under the same scope/model/reducer policy. Never average posterior means or covariances.

Bayesian updating is nonlinear. In general:

\[
\operatorname{Fit}(E_A\cup E_B)
\ne
\frac12\left(\operatorname{Fit}(E_A)+\operatorname{Fit}(E_B)\right).
\]

The union history plus representation scope, model/reducer policy, and declared merge prior is the operational definition of a merge. Evidence alone is insufficient when independently spawned components have different base priors.

### Blend or crossover

Generate a candidate between two taste regions, but mutate neither taste. Blend is a proposal operation. Merge is an evidence/model operation. They must not share a button or event type.

### Dormancy and retraction

Dormancy changes display/proposal eligibility without deleting evidence. A branch-local Undo creates a descendant that excludes the targeted event while sibling forks remain intact. Global invalidation is reserved for corrupt source facts and explicitly rebuilds every affected descendant. Neither operation adds a manufactured negative event.

## Why unconstrained automatic splitting fragments

The maximized likelihood of a \(K+1\)-component mixture cannot be lower than the maximized likelihood of a \(K\)-component mixture, because the larger model can assign the extra component zero weight and reproduce the smaller model.

Therefore raw in-sample likelihood always weakly favors extra capacity. With sparse observations, a new component can specialize to a single surprising event. This is the taste-level version of the current one-click-one-concept failure.

A hidden two-component ideal-point mixture adds roughly \(d+1=9\) free parameters over one component at \(d=8\). A rough regular-model BIC gate would demand:

\[
2(\ell_2-\ell_1)>9\log n.
\]

Finite mixtures violate some regular BIC assumptions, so this is a warning scale, not the production rule. Use held-out or prequential choice likelihood, minimum evidence per child, multiple independent anchors, and user confirmation. Automatic split/merge should remain disabled until explicit components have proven useful.

## Taste modes are not composable attributes

This is the most important product distinction after learner ownership.

A v1 family is an explicitly activated **OR** collection. If branch \(b\) names taste \(z_b=k\), its predictive choice distribution is:

\[
P(y\mid A,z_b=k)=m_k(y,A).
\]

A later latent-activation treatment would be a genuine mixture:

\[
P(y\mid A)=\sum_k\pi_km_k(y,A).
\]

Both preserve alternative component predictions. Replacing them with one averaged target does not.

Composable attributes are an **AND** or factor model:

\[
u(x)=\lambda_Au_A(x)+\lambda_Bu_B(x).
\]

The same collapse appears if two opposite utility functions are averaged. If:

\[
u_A(x)=x,
\qquad
u_B(x)=1-x,
\]

then averaging gives:

\[
\frac12u_A(x)+\frac12u_B(x)=\frac12
\]

everywhere. The point is not that utilities and densities are interchangeable; it is that an OR family must preserve alternative components rather than replace them with one averaged component.

Conversely, one accepted image does not identify the attributes that caused acceptance. Suppose observations only compare actions on the line:

\[
a=(s,s),
\]

under linear factor utility:

\[
u(a)=\beta_1a_1+\beta_2a_2.
\]

Every observed utility depends only on \(s(\beta_1+\beta_2)\). Infinitely many pairs \((\beta_1,\beta_2)\) give identical choices. No clustering threshold can recover the separate factors without counterfactual interventions that vary them independently.

Therefore v1 should learn and expose alternative taste regions. It should not call them reusable attributes. Attribute discovery requires repeated controlled contrasts, visual-delta evidence, and demonstrated transport through the renderer.

## Is this a genetic algorithm?

No. The genealogy metaphor is useful, but the inference problem is closer to a finite Bayesian mixture or filter.

Interactive evolutionary computation evolves a population of candidate **designs** through human evaluation, selection, mutation, and crossover ([`TAKAGI-2001`](CITATION_LEDGER.md#takagi-2001)). It can be a useful proposal engine. It does not by itself provide:

- a calibrated posterior over taste;
- an exposure-correct slate likelihood;
- stable dormant taste modes;
- exact event replay;
- an explicit distinction between uncertainty and taste breadth.

A particle filter can look evolution-like because it reweights, resamples, and jitters hypotheses. But particles normally approximate one latent distribution; resampling can erase dormant interests. Durable named tastes and particle hypotheses are different objects.

Use mutation, crossover, CMA-ES, or MAP-Elites later if they generate better candidate actions. They should consume the `TasteFamily`; they should not own it.

## What Evan Shimizu's work actually does

Shimizu et al.'s [Design Adjectives paper](https://graphics.cs.cmu.edu/projects/design-adjectives/assets/adjectives.pdf), [thesis](https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf), and [released code](https://github.com/ebshimizu/DesignAdjectives/tree/cacfbbaebe13b21c44e55738c2260a0e3312022c) use one explicitly created adjective with its own scored-example history and Gaussian-process regression model. Several adjectives can exist, but the validated system does not automatically assign, spawn, split, or merge them.

The sampler is evolution-like in one narrow sense: it starts from positively scored examples, replaces a random subset of design parameters, and rejects proposals that do not satisfy a condition on the GP mean. The code also contains a parameter mixer analogous to crossover. Both operations produce **design parameter vectors**; neither evolves adjective models or taste histories.

The main interaction operations are Towards, Away, Similar Score, and Axis. Axis spreads samples across levels of one learned scalar score. It is not a linear control-space direction such as \(x_0+td\). Any `-2d, -d, current, +d, +2d` direction sweep is an Art Optimizer proposal, not a result attributable to Shimizu.

The citation-safe conclusion is:

> Shimizu implements separately named, example-backed design adjectives and discusses multi-adjective interfaces. Those adjectives are user-defined subjective concepts, not evidence that the system discovers alternative persistent taste modes. The work does not supply automatic multimodal taste inference, genetic evolution of tastes, or reinforcement learning.

What Art Optimizer should borrow is discipline:

- one canonical labeled history per subjective model;
- a small few-shot probabilistic learner;
- an explicit bounded parameter space;
- different sampling commands that query the same learner;
- inspectable examples and easy human correction.

The GP kernel is a smoothness prior over a subjective function. It is not an “Evan prior” over a persistent family of tastes. A GP per taste is a reasonable later component model if the ideal-point assumption fails predictive tests.

## Why not reinforcement learning yet

Reinforcement learning optimizes a policy for expected cumulative future reward ([`SUTTON-BARTO-2018`](CITATION_LEDGER.md#sutton-barto-2018)). The present primitive is an immediate exposed-slate judgment used to estimate latent preference and choose the next query. That is active preference learning or a contextual/slate bandit problem ([`BROCHU-APL-2007`](CITATION_LEDGER.md#brochu-apl-2007), [`PBO-2017`](CITATION_LEDGER.md#pbo-2017)), not yet a defensible long-horizon control problem.

RL does not resolve what the user liked in an image, whether a click belongs to a new taste, or whether the control basis expresses that taste. Adding it now would move uncertainty into a less inspectable policy.

There is a stronger issue. If the system's recommendations change what the user comes to prefer, an RL objective can optimize taste formation rather than merely infer taste. That may eventually be an intentional research question, but it requires explicit rewards, horizons, safety constraints, and evaluation. It is not a primitive to add casually.

## A fundamental ambiguity no algorithm removes

Choice sequences alone cannot generally distinguish:

1. one taste drifting over time; from
2. several stable tastes whose activation switches over time.

A sufficiently flexible drifting state can reproduce a switching sequence. A mixture with enough components and flexible assignments can reproduce an arbitrary drift sequence. Context, dynamics priors, repeated probes, or explicit user labels are required to choose between the explanations.

That is why v1 should make Spawn, Switch, and Fork explicit. The system may suggest structure after sustained predictive failure; it should not present a split inferred from three clicks as discovered truth.

## The planner from the same belief

The planner should consume the active component posterior, not maintain another preference representation.

For posterior \(\theta\sim\mathcal N(m,C)\), expected ideal-point utility is:

\[
\mathbb E[u(a)]
=-\frac{1}{2}\left[(a-m)^TQ(a-m)+\operatorname{tr}(QC)\right].
\]

The trace term is constant across actions in one round, so exploitation is simply movement toward \(m\) under \(Q\), subject to a trust region and renderer validity.

For \(\delta=a-a_0\), uncertainty in relative log utility is:

\[
\operatorname{Var}\left[
\frac{u(a)-u(a_0)}{\tau}
\right]
=\frac1{\tau^2}\delta^TQCQ\delta.
\]

The leading eigendirections of \(QCQ\) are uncertainty directions, not automatically information-optimal queries. A saturated comparison can have large latent variance but little expected Fisher information. Construct balanced alternatives near predicted indifference, then score a proposed slate by expected Fisher information or expected log-determinant reduction:

\[
\mathbb E_{\theta\sim q}
\left[
\log\det\left(
C^{-1}+\frac{1}{\tau^2}Q\operatorname{Cov}_{p_\theta}(a)Q
\right)
\right].
\]

An alternate-taste candidate can come from another explicitly selected component. An outside candidate can deliberately test beyond the family.

Rendered-image duplicate detection remains necessary. It is a measurement in the proposal/rendering policy, not another taste learner.

## Scope limit: representation still dominates

Unifying the learner does not repair a weak renderer chart.

An action-space taste is controllable but model-, prompt-, and basis-local. An image-space taste can persist across worlds but cannot generate actions without a learned transport or reference-conditioned renderer. No preference-learning algorithm removes that bridge.

The current FLUX direction bank is prompt-conditioned. Therefore v1 components must be scoped to an exact `ControlBasisID` that identifies the concrete direction bank and prompt/model revision. Numeric action means from incompatible banks must never be averaged. The utility curvature \(Q\) belongs to the versioned taste-model policy, not renderer identity, so the same raw events can be refit under an ablated \(Q\).

This makes the immediate order clear:

1. validate or calibrate the eight-dimensional chart;
2. make one small action-space taste model authoritative;
3. test transfer before calling it persistent cross-prompt taste;
4. later add a versioned visual representation and explicit transport if the product requires global visual memory.

## Non-negotiable invariants

1. One authoritative append-only event history and server-side `TasteState` projection; each contained `TasteFamily` is homogeneous in representation scope.
2. One active taste component per branch in v1.
3. Every preference event appears at most once in any component revision's evidence closure; forked heads may share immutable ancestral evidence without applying it twice within either head.
4. Replay under a fixed reducer revision is deterministic.
5. Preview, broken render, More Variety, New World, revisit, and ordinary favorite toggles do not update taste.
6. `NoneOfThese` is an explicit anchor-wins observation; it is not `MoreVariety`.
7. Posterior covariance and utility curvature \(Q\) remain distinct: approximate geometric width scales with \(Q^{-1/2}\), while covariance represents epistemic uncertainty.
8. Split and merge operate on evidence IDs and replay, never posterior averaging.
9. Named tastes are never silently merged, split, deleted, or reassigned.
10. UI state is a projection of server state, never an independent browser learner.
11. Branch restoration points to an exact immutable taste revision; it never destroys later history.
12. Components do not cross incompatible representation scopes without validated transport.
13. Generation changes pixels; only a subsequent typed user event may change taste.
14. Active pointers resolve to nonarchived, scope-compatible component revisions; revision ancestry is acyclic.
15. Posterior covariance and \(Q\) are positive definite, \(\tau>0\), evidence is scope/prior compatible, and revision ancestry is acyclic.
16. An action-only preference update requires one controlled prompt/seed/noise context and randomized or counterbalanced UI position; a mixed-seed, cross-prompt, or position-confounded selection is recorded but receives zero action-taste weight until an appropriate nuisance/context model exists.

## Final decision

Adopt one learner type with many explicit taste instances:

```text
immutable, typed, exposed-slate history
        ↓
one deterministic TasteState reducer
        ↓
homogeneous scoped families of small posterior components
        ↓
planner + New World + every UI read the same state
```

Begin with \(K=1\), the eight-parameter ideal-point model, and explicit Spawn/Switch/Fork. Disable automatic split/merge, browser-local concept learning, atlas clustering, GP complexity, sequence priors, and RL in the primitive experiment.

This is the first treatment, not a permanent algorithm monopoly. The [engine/UI ablation matrix](14B_TASTE_ENGINE_UI_ABLATION_MATRIX.md) defines how alternative learners and data projections can compete while exactly one assigned engine owns any live session.

The target contribution is not “a genetic art optimizer.” It is a replayable, multi-component-capable preference state whose uncertainty and lineage remain visible while the renderer and proposal policy improve around it. Actual multimodal usefulness is a claim to earn in the explicit two-taste experiment, not a property established by this architecture document.
