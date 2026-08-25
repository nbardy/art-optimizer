# Emergent Tastes Runtime Treatment

**Route:** `/ui/emergent-tastes`  
**Treatment ID:** `emergent-tastes`

## Goal

Test whether repeated fixed-root choices are better predicted by one or several latent action-preference modes while candidate generation remains the T0 control policy.

## Observation

Each qualified observation contains:

- exact anchor and exposed alternatives;
- action vectors and rendered design identities;
- winner and evidence weight;
- model/renderer/codec/conditioning/basis/prompt/seed scope;
- result checkpoint;
- predictions made before the outcome was learned.

The event protocol is:

```text
emergent_taste_choice_pending
    -> base command commits
    -> emergent_taste_choice_recorded
```

On restart, a pending fact is finalized when the matching durable base event exists. Thus the preference fact is recoverable even if the process stops between the two writes.

## Model

For taste mode \(k\) with ideal point \(\theta_k\):

\[
u_k(a)=-\frac{\beta}{2}\lVert a-\theta_k\rVert^2.
\]

A multinomial softmax predicts the selected anchor/candidate. Hidden modes follow:

\[
P(z_t=j\mid z_{t-1}=i)
=\rho\mathbf 1[i=j]+(1-\rho)\frac1K.
\]

The prevalence is intentionally uniform in this baseline. Normalized state occupancies are not used as a false M-step for the sticky transition model.

An observation with weight \(\omega_t\) contributes the power likelihood:

\[
p(y_t\mid z_t=k)^{\omega_t}.
\]

The same quantity is used in fitting and chronological model scoring. EM convergence is evaluated after recomputing likelihood under the newly updated centers. Old stored sessions retain their original prequential receipt semantics during replay.

Models with one, two, and three modes are scored before each vote. Additional modes require enough evidence, convergence, and penalized chronological improvement.

## Interpretation

A displayed Taste A/B/C is a coherent region of action-choice behavior. Images are exemplars attached to that inferred mode. The runtime does not yet infer a visual attribute from image embeddings or prove cross-prompt transfer.

## Candidate policy

The legacy T0 planner remains authoritative in this treatment. This isolates the latent-mode inference/UX question from planner replacement. A separate future treatment may test taste-authoritative planning after representation validation.
