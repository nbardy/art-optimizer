# Research Review 3/5: Preference Learning and Preferential Bayesian Optimization

## 1. Review question

How should a system learn a user's local visual preference from repeated choices among generated candidates, and how should it choose the next candidates when each human judgment is expensive?

The relevant literature spans:

- Gaussian-process preference learning;
- active preference learning from discrete choice;
- preferential Bayesian optimization;
- human-in-the-loop graphics optimization;
- multi-choice image optimization;
- contextual and nonstationary preference models.

The central engineering conclusion is:

> The online problem is initially a contextual, preferential, slate-selection problem—not full reinforcement learning and not ordinary supervised regression.

## 2. Preference observations versus numeric rewards

Let \(a\in\mathcal A\) be an action in a generator control space and \(f(a)\) a latent subjective utility. Direct regression assumes observations such as:

\[
y_i = f(a_i) + \epsilon_i.
\]

Visual users are often more reliable when comparing alternatives than when assigning a globally calibrated score. Pairwise preference learning instead observes:

\[
a_i \succ a_j.
\]

A common probit model is:

\[
P(a_i \succ a_j)
=\Phi\left(
\frac{f(a_i)-f(a_j)}{\sqrt{2}\sigma}
\right),
\]

while a Bradley–Terry/logistic model uses:

\[
P(a_i \succ a_j)
=\sigma\left(
\frac{f(a_i)-f(a_j)}{\tau}
\right).
\]

[Chu and Ghahramani (2005)](https://doi.org/10.1145/1102351.1102369) provide an influential Gaussian-process formulation for preference relations. [Brochu, de Freitas, and Ghosh (2007)](https://papers.nips.cc/paper_files/paper/2007/hash/b6a1085a27ab7bff7550f8a3bd017df8-Abstract.html) connect active discrete-choice learning directly to graphics/material parameter search.

## 3. The Art Optimizer observation is multi-choice

A four-candidate round is not naturally three independent pairwise labels. The user sees a slate:

\[
S_t = \{a_{t0},a_{t1},\ldots,a_{tm}\},
\]

where \(a_{t0}\) is the committed current design and \(a_{t1:m}\) are meaningfully exposed candidates.

A multinomial-logit observation is:

\[
P(y_t=j\mid S_t,w)
=
\frac{\exp(f_w(a_{tj})/\tau)}
{\sum_{k=0}^{m}\exp(f_w(a_{tk})/\tau)}.
\]

The anchor is not a dummy option. It has an exact product meaning:

- \(y_t=j>0\): candidate \(j\) was worth replacing the current design;
- \(y_t=0\): the current design won; this is a valid reroll observation when the alternatives were actually exposed.

Using one slate likelihood avoids pretending that the three implied comparisons are conditionally independent.

### 3.1 Why exposure belongs in the likelihood

The choice set must contain only alternatives the user could judge. A queued, failed, off-screen, or never-loaded candidate is not a loss.

Let \(e_{tj}\in\{0,1\}\) be meaningful exposure. The effective slate is:

\[
S_t^{\mathrm{obs}}
=\{a_{t0}\}\cup\{a_{tj}:e_{tj}=1\}.
\]

This is more than analytics hygiene. Mislabeling unseen images as rejected biases the model toward whatever happened to render first and teaches it from infrastructure failures.

## 4. Preferential Bayesian optimization

[Preferential Bayesian Optimization](https://proceedings.mlr.press/v70/gonzalez17a.html) generalizes Bayesian optimization to objectives that can only be queried through comparisons. The latent utility receives a probabilistic surrogate; an acquisition policy chooses the next duel to balance likely value and information.

A generic acquisition score can combine:

\[
A(a)
=\mu(a)+\beta\sigma(a),
\]

or draw a posterior function:

\[
\tilde f\sim p(f\mid\mathcal D),
\qquad
a^*=\arg\max_a\tilde f(a).
\]

The first resembles an upper confidence bound. The second is Thompson sampling.

For Art Optimizer, one scalar acquisition is insufficient because a quartet must be useful **as a set**. If all four candidates maximize the same UCB score, the UI will often receive four near-duplicates.

## 5. Slate acquisition

The displayed set should jointly optimize preference, information, and diversity:

\[
S^*
=\arg\max_{|S|=4}
\left[
\sum_{a\in S}
\bigl(\mu(a)+\beta\sigma(a)\bigr)
+\lambda_D\log\det(K_S)
-\lambda_J\sum_{a\in S}D(a,a_0)
\right].
\]

Interpretation:

- \(\mu(a)\): expected utility improvement;
- \(\sigma(a)\): uncertainty/information potential;
- \(\log\det K_S\): set diversity;
- \(D(a,a_0)\): jump distance from the current anchor;
- \(\lambda_J\): keeps most proposals coherent with the active branch.

The current implementation approximates this with four policy roles:

1. best local continuation;
2. diverse posterior sample;
3. informative probe;
4. controlled surprise or alternate persistent mode.

The role decomposition is not a theorem. It is a transparent finite-policy approximation to a difficult slate-acquisition problem.

## 6. Human-in-the-loop graphics ancestry

[Brochu, Brochu, and de Freitas (2010)](https://doi.org/10.2312/SCA/SCA10/103-112) apply Bayesian interactive optimization to procedural animation parameters, using prior knowledge and user feedback to reduce the number of trials. Their work and the earlier active-preference paper establish that subjective graphics parameters can be optimized from discrete judgments rather than explicit analytic objectives.

[Sequential Gallery](https://doi.org/10.1145/3386569.3392444) decomposes high-dimensional visual search into sequential two-dimensional plane-search queries and uses gallery selection to make those queries answerable. This emphasizes an important HCI point: acquisition functions must generate **judgment tasks humans can actually perform**, not only mathematically informative points.

## 7. Multi-choice image optimization

[MultiBO](https://arxiv.org/abs/2602.02388) is the closest recent preference-optimization analogue for modern image generation. It presents multiple generated alternatives, collects multi-choice preference, and optimizes a constrained transformation space around a target-oriented image-generation task.

Its relevance:

- preference remains available after prompting reaches a language limit;
- one multi-choice query extracts more information than one binary duel;
- the control space can be a compact attention intervention rather than raw noise;
- a human query budget should be treated as scarce.

Its boundary relative to Art Optimizer:

- MultiBO is framed around approaching an implicit target image;
- Art Optimizer is often open-ended and inspiration can change the target;
- Art Optimizer retains cross-session taste modes and a branch forest;
- Art Optimizer treats the current design as an explicit outside option.

## 8. Why v0 uses a Bayesian linear model

A pairwise Gaussian process is attractive for very small datasets, but a full GP creates several early implementation choices:

- kernel family;
- length-scale priors;
- approximate inference;
- cubic scaling with observations;
- treatment of nonstationarity;
- and numerical behavior under many nearly redundant choices.

Art Optimizer instead uses a Bayesian linear utility over quadratic action features:

\[
\psi(a)
=
\left[
 a_1,\ldots,a_d,
 a_1^2,\ldots,a_d^2,
 \{a_i a_j\}_{i<j}
\right],
\]

\[
f(a)=w^\top\psi(a),
\qquad
w\sim\mathcal N(0,\lambda^{-1}I).
\]

A Laplace approximation produces:

\[
q(w)=\mathcal N(\hat w,\Sigma_w).
\]

This model is a pragmatic first surrogate because it is:

- cheap to update after each command;
- deterministic and testable;
- uncertainty-aware;
- expressive enough for curvature and pairwise coordinate interactions;
- small enough to inspect;
- replaceable through the preference-model factory.

It should not be defended as universally superior to a GP. Its purpose is to make the interaction and acquisition loop executable while the control basis and actual data regime are still being learned.

## 9. Nonstationary preference

Creative preference is not necessarily a fixed utility function. [SwipeGANSpace](https://arxiv.org/abs/2404.19693) reports that exposure to novel images can inspire users and alter what they prefer during the session.

A basic recency-weighted objective is:

\[
\mathcal L_t(w)
=\sum_{s\le t}\gamma^{t-s}\ell_s(w),
\qquad 0<\gamma\le1.
\]

Covariance inflation or forgetting prevents old branch evidence from dominating a new direction indefinitely.

But forgetting alone is not enough. Art Optimizer separates:

- a local posterior that may change rapidly;
- a persistent atlas that keeps older coherent modes dormant rather than erasing them.

This gives the system a way to say “the current project changed” without concluding “the user no longer likes that other style.”

## 10. Reroll ambiguity

The current reroll semantics are mathematically clean:

> the anchor beat the meaningfully exposed candidates.

Behaviorally, reroll can still mean several things:

1. every candidate is worse;
2. candidates are acceptable but the user wants more options;
3. candidates are too similar;
4. the branch is stale;
5. the renderer produced artifacts;
6. the user did not understand the differences.

Therefore reroll should remain:

- weaker than a commit;
- separate from persistent dislike;
- excluded when too few alternatives were exposed;
- accompanied by product research on reason codes before its weight is increased.

A future optional reason prompt might appear only after repeated rerolls:

```text
What should change?
[more different] [better quality] [wrong direction] [just more options]
```

That should be an explicit augmented signal, not inferred from dwell or frustration.

## 11. Preference inconsistency

A latent scalar utility implies transitivity. Real creative judgments may be contextual or cyclic:

\[
a\succ b,\quad b\succ c,\quad c\succ a.
\]

[Chau, Gonzalez, and Sejdinovic (2022)](https://proceedings.mlr.press/v151/lun-chau22a.html) explicitly study inconsistent GP preferences and richer preferential structure.

Art Optimizer should first treat occasional cycles as expected noise. If systematic cycles appear, possible explanations include:

- multi-interest taste;
- context-dependent comparison;
- novelty seeking;
- fatigue;
- or a control space that changes unrelated attributes.

A more complex preference model is justified only after the event data demonstrates this failure mode.

## 12. Bandit versus reinforcement learning

The current loop is well modeled as a contextual slate/dueling bandit:

```text
context
    current world, anchor, history, atlas responsibilities

action
    four-candidate slate

observation
    chosen candidate or anchor

immediate objective
    useful preference information and progress
```

Full reinforcement learning becomes relevant when optimizing long-horizon effects:

- showing a surprising image now to unlock a new interest later;
- managing novelty fatigue;
- deciding when to ask explicit calibration questions;
- balancing completion against open-ended discovery;
- or planning across sessions.

Until those effects are measured, policy-gradient RL adds variance and opacity without solving the primary control-space problem.

## 13. Offline generator adaptation

Online candidate selection and offline model adaptation should remain separate.

Once enough preference pairs exist, methods such as [DRaFT](https://arxiv.org/abs/2309.17400) and [Diffusion-DPO](https://arxiv.org/abs/2311.12908) offer ways to consolidate preference into adapters or model weights.

The online loop should not fine-tune after every click because that would be:

- slow;
- hard to reverse;
- vulnerable to transient intent;
- prone to collapse;
- and difficult to attribute.

A better cadence is:

```text
online
    posterior update + candidate planning

offline
    validated preference dataset -> adapter/reward/model update
```

## 14. Evaluation requirements

### Predictive evaluation

- held-out slate-choice log likelihood;
- pairwise/multi-choice accuracy;
- calibration and Brier score;
- uncertainty calibration;
- sensitivity to exposure masking;
- performance under synthetic drift.

### Optimization evaluation

- simple regret under simulated utilities;
- rounds to first favorite/export;
- “none of these” rate;
- candidate diversity;
- recovery after one misleading choice;
- robustness to artifact candidates.

### Human evaluation

- perceived progress;
- cognitive effort per round;
- confidence in choices;
- feeling of control;
- discovery versus repetition;
- ability to recover an earlier branch;
- satisfaction with final saved outputs.

## 15. Citation-safe conclusion

The preference-learning literature supports modeling visual judgments as noisy comparisons over a latent utility and using posterior uncertainty to choose informative future candidates. Art Optimizer's four-way interaction is naturally represented as a multinomial choice among the current anchor and meaningfully exposed candidates. Its current quadratic Bayesian surrogate is a deliberately simple implementation choice; preferential GPs, neural dueling bandits, and long-horizon policies remain replaceable research alternatives.

## References

- Wei Chu and Zoubin Ghahramani. [“Preference Learning with Gaussian Processes.”](https://doi.org/10.1145/1102351.1102369) ICML, 2005.
- Eric Brochu, Nando de Freitas, and Abhijeet Ghosh. [“Active Preference Learning with Discrete Choice Data.”](https://papers.nips.cc/paper_files/paper/2007/hash/b6a1085a27ab7bff7550f8a3bd017df8-Abstract.html) NeurIPS, 2007.
- Eric Brochu, Tyson Brochu, and Nando de Freitas. [“A Bayesian Interactive Optimization Approach to Procedural Animation Design.”](https://doi.org/10.2312/SCA/SCA10/103-112) SCA, 2010.
- Javier González, Zhenwen Dai, Andreas Damianou, and Neil D. Lawrence. [“Preferential Bayesian Optimization.”](https://proceedings.mlr.press/v70/gonzalez17a.html) ICML, 2017.
- Yuki Koyama, Issei Sato, and Masataka Goto. [“Sequential Gallery for Interactive Visual Design Optimization.”](https://doi.org/10.1145/3386569.3392444) ACM TOG, 2020.
- Siu Lun Chau, Javier Gonzalez, and Dino Sejdinovic. [“Learning Inconsistent Preferences with Gaussian Processes.”](https://proceedings.mlr.press/v151/lun-chau22a.html) AISTATS, 2022.
- Yuto Nakashima, Mingzhe Yang, and Yukino Baba. [“SwipeGANSpace: Swipe-to-Compare Image Generation via Efficient Latent Space Exploration.”](https://arxiv.org/abs/2404.19693) 2024.
- Rajalaxmi Rajagopalan, Debottam Dutta, Yu-Lin Wei, and Romit Roy Choudhury. [“Personalized Image Generation via Human-in-the-loop Bayesian Optimization.”](https://arxiv.org/abs/2602.02388) 2026.
- Kevin Clark, Paul Vicol, Kevin Swersky, and David J. Fleet. [“Directly Fine-Tuning Diffusion Models on Differentiable Rewards.”](https://arxiv.org/abs/2309.17400) 2023.
- Bram Wallace et al. [“Diffusion Model Alignment Using Direct Preference Optimization.”](https://arxiv.org/abs/2311.12908) 2023.
