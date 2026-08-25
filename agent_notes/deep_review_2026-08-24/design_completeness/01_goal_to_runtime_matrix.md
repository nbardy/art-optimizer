# Track DC-1 — Goal-to-Runtime Completeness Matrix

## Executive finding

The current runtime implements a recognizable and usable slice of the intended product:

- fixed-root ordinary voting;
- embedding/action candidate variation;
- neutral exploration distinct from rejection;
- an online latent-mode projection;
- taste cards;
- a seed-by-strength gallery;
- fresh sessions from gallery cells.

However, it does **not** yet implement the stronger scientific goal that motivated “emergent tastes”: learning coherent tastes from sets of images and continually validating those tastes as generative families.

The right summary is:

```text
UX concept implementation:             approximately two-thirds complete
choice-space latent-mode prototype:    approximately half complete
image-set / reusable-attribute model:  largely not implemented
```

Those are qualitative estimates, not project-management percentages.

## Goal matrix

| Intended goal | Current implementation | Assessment |
|---|---|---|
| All UIs available as experiments | `/` catalog and stable `/ui/...` routes in [`app.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/app.py) | Implemented |
| Fixed seed during embedding ablation | all candidate renders in one world use `world.seed` in [`service._render_candidate`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py) | Implemented |
| Candidate variance from embeddings/actions | T0 planner proposes eight-dimensional action changes; renderer uses authored prompt-embedding directions | Implemented, representation unvalidated |
| “More variety” does not mean dislike | emergent `New directions` calls reroll with an empty exposure set | Implemented in emergent UI only |
| Explicit “None fit” preference | emergent wrapper records a weak anchor win and base reroll updates legacy learner | Implemented, with persistence caveats |
| Tastes emerge without manual creation | sticky finite mixture selects one, two, or three ideal points | Implemented as action-choice modes |
| Continually predict, then train | observed-winner probability is recorded before refit | Partially implemented |
| Learn tastes from a set of images | model likelihood uses action vectors and choices; images are display exemplars only | Not implemented |
| Extract reusable attributes across images | no representation learner or held-out transfer tests | Not implemented |
| Stable taste identities | tastes are relabeled by current hard assignments and first-seen order | Not implemented |
| Click a taste to browse it | gallery is attached to taste cards | Implemented |
| Gallery rows = seeds, columns = strength | `a = clip(strength * center)` and deterministic seed rows | Implemented |
| Gallery browsing does not train | no emergent choice event is appended | Implemented |
| Continue from a gallery cell | creates a fresh fixed-root session at exact seed/action | Implemented, provenance incomplete |
| Configurable mathematical ablations | constructor parameters exist but session/API/UI always instantiate defaults | Not implemented |
| One authoritative taste state per treatment | legacy branch learner, atlas, browser concepts, and emergent projection coexist | Not implemented |
| Taste-authoritative planning | legacy T0 learner remains authoritative | Explicitly deferred |
| True image evolution | selected pixels/latent are not parent conditioning | Explicitly not implemented |

## 1. “Emergent taste” currently means action-space mode

The model in [`emergent_taste.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py) receives:

```text
anchor action
candidate actions
winner
chronological position
```

It does not receive image embeddings, visual deltas, captions, or a generative-consistency measurement. The exemplar images shown in the rail are selected after the fit from hard assignments.

Therefore a taste means:

> a temporally persistent ideal-point region that explains choices over the current authored control coordinates.

It does not yet mean:

> a coherent distribution of visual outcomes extracted from multiple images.

That distinction should remain explicit in UI and documentation.

## 2. “Continually test” is only a scalar prequential test

Before each vote, every candidate `K` model stores one number:

```python
P(the eventually observed winner | current model K, slate)
```

This supports cumulative log score. It does not store the full categorical distribution. Consequently the system cannot later compute:

- calibration by predicted probability bin;
- Brier score;
- confusion/residual structure across candidates;
- whether a model was confidently wrong about a particular alternative;
- position- or role-conditioned residuals.

The implemented test is valuable, but narrower than “continually train and test tastes.”

## 3. Gallery is a visualization, not a validation protocol

The seed-by-strength gallery in [`taste_gallery.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/taste_gallery.py) is an excellent inspection primitive. It currently does not answer whether the taste generalizes:

- no cross-seed coherence statistic;
- no held-out human judgment event;
- no comparison against a neutral or alternate taste;
- no uncertainty band over the taste center;
- no distinction between interpolation toward a center and expression of a stable visual family.

The gallery should be described as a probe until a validation protocol exists.

## 4. Configurability exists only in source code

`EmergentTasteEngine` exposes constructor parameters for persistence, temperature, prior variance, component count, penalties, and iteration count. But [`EmergentTasteExperiment._load_cache`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_experiment.py) always calls:

```python
engine = EmergentTasteEngine(dimension)
```

`CreateSessionRequest` has only prompt and seed. The UI has no experiment configuration. Events have no model-policy digest.

Thus the runtime does not implement the configurable ablations described in prior conversation or PR text.

## 5. The initial condition is confounded by legacy atlas guidance

Emergent session creation delegates to `ArtOptimizerService.create_session`, which chooses persistent-atlas guidance and may blend it into the root action. The legacy planner also uses atlas biases and an alternate atlas component.

So the treatment called “emergent tastes” begins and proposes candidates using an older persistent taste system. This is not a clean ablation of emergent inference.

A controlled treatment should state one of:

```text
neutral root, no atlas, legacy planner
neutral root, no atlas, emergent shadow
atlas-guided root, explicitly declared covariate
```

The current path is the third but the UI implies the second.

## 6. Legacy semantics remain visible

The emergent UI has truthful `New directions` and `None fit`, but the baseline and concept variants still expose `Reroll`, and browser `ConceptLibrary.observeReroll` adds opposition. The repository therefore does not have one corrected product; it has one corrected treatment beside legacy semantics.

That is acceptable for a preserved baseline, provided the catalog labels it as a legacy control rather than a peer product.

## 7. Completeness target

A complete model of the new goal would require:

1. an explicit `TreatmentConfiguration` frozen per session;
2. no undeclared atlas/concept mutation in the emergent treatment;
3. full predictive distributions and calibration receipts;
4. persistent component identity/lineage;
5. image-set or visual-consistency diagnostics for each taste;
6. gallery probe outcomes that are typed separately from preference votes;
7. held-out cross-seed/cross-anchor validation before calling a taste a generative family;
8. a later separate treatment where the taste posterior proposes candidates.

## Verdict

**Did we implement the UI idea?** Largely yes.  
**Did we implement an online mixture of action preferences?** Yes, as a prototype.  
**Did we implement natural tastes extracted from sets of images?** No.  
**Did we implement a clean experiment?** Not yet; the treatment is confounded by legacy learner and atlas behavior.  
**Most important wording correction:** call the current object an “emergent action-preference mode” until cross-image generative coherence is demonstrated.
