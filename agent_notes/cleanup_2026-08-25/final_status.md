# Cleanup Final Status

## Scope

This pass intentionally changed no product promise, renderer family, candidate count, or visible experiment surface. It merged the audit, corrected the current fixed-root treatment, removed stale infrastructure, and made repository descriptions match runtime behavior.

## Audit findings resolved

| Finding | Resolution |
|---|---|
| Qualified emergent vote could be lost between two writes | Added durable pending/final facts and restart recovery from the committed base event |
| `None fit` posterior could disappear after history restoration | Every reroll/skip now creates a same-design branch checkpoint with the current posterior and search state |
| Sticky-HMM prevalence update did not match its declared transition | Baseline now uses explicit uniform prevalence; no false occupancy M-step |
| EM convergence mixed old likelihood with new parameters | Likelihood and prior are recomputed at one consistent updated iterate |
| Weak evidence was weighted differently in fitting and scoring | New facts use one power-likelihood quantity; old receipts retain legacy replay semantics |
| Missing prediction receipts were silently replaced | Replay now rejects incomplete mathematical evidence |
| Gallery could launch 42 unbounded renders | Added bounded concurrency, per-session serialization, and failure cleanup |
| Request IDs could be reused for different emergent/gallery commands | Pending facts and gallery operations validate command identity before replay |
| Representation scope was too weak | New observations include model, renderer, codec, conditioning mode, basis, prompt, seed, and dimension |
| Monolithic taste/gallery files obscured data flow | Split typed contracts, pure math, projection formatting, bounded rendering, and activation adapters |
| Hosted Actions created noise and false failures | Removed the workflow; `make check` is the explicit local gate |
| Documentation overstated visual-taste inference | Runtime and docs now say latent action-preference modes and preserve explicit non-claims |

## Compatibility

- Existing UI routes and API paths are unchanged.
- Old recorded taste observations load with defaults for new scope fields.
- Old prequential receipts keep their original weighting semantics during replay.
- Existing `emergent_taste` imports are re-exported from the smaller modules.
- Gallery IDs, cell geometry, and no-vote semantics remain unchanged.

## Verification performed during the pass

- Python syntax compilation for every new or replaced module;
- synthetic one-, two-, and three-mode recovery;
- brute-force hidden-path comparison for forward-backward inference;
- weak-evidence power-likelihood consistency;
- legacy/new receipt score equivalence;
- repository TODO/FIXME search;
- GitHub changed-file and route/API compatibility review.

The repository-local gate is `make check`; the user should run it in the normal development environment before the GPU session.

## Remaining work is research, not cleanup debt

The following are intentionally separate gates rather than hidden TODOs in this treatment:

1. validate authored controls on real FLUX/Krea runs;
2. compare a taste-authoritative planner against the current control treatment;
3. extract reusable directions only after held-out transfer tests;
4. implement true parent-conditioned evolution as a separate renderer treatment.
