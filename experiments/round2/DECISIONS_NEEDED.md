# Round 2 Decisions Needed

These are product-definition questions, not details the optimizer can infer from code. Defaults are proposed so implementation can proceed, but they should be changed when direct user intent says otherwise.

## 1. Primary promise

Choose the dominant experience:

- **A — surprising generative search:** find images and conditioning regions that are difficult to prompt;
- **B — true image evolution:** select an image and preserve recognizable qualities in descendants;
- **C — reusable visual concepts:** learn recurring properties and compose them across realizations.

**Proposed default:** A first, B as the first divergent comparison, C after visual evidence exists.

## 2. Meaning of “concept”

Which objects matter most?

- material/texture;
- lighting relation;
- palette;
- composition/layout;
- recurring object or motif;
- mood/style distribution;
- transformation from one image to another;
- holistic “this feels right” preference mode.

Different answers require different representations. A transformation is naturally a visual delta; an object requires identity/semantic features; a mood may be a distribution over images.

**Input requested:** 3–5 positive examples and 2 near-misses for two or three desired concept types.

## 3. Extra interaction burden

Possible levels:

- **zero:** infer only from choice/shuffle/favorite;
- **occasional diagnostic:** sometimes ask why a selection was made;
- **gesture distinction:** click = best image, modified click = save this move/attribute;
- **explicit workbench:** examples, counterexamples, merge/split, sweeps.

**Proposed default:** zero for normal rounds, one optional `Save move` action, and occasional diagnostic comparisons only when information gain is high.

## 4. Candidate wildness

Choose the normal slate character:

- mostly subtle refinement;
- one safe, two medium, one wild;
- broad exploration every round;
- explicit wild/another-realization command.

**Proposed default:** one safe same-root, one strong same-root, one correlated/fresh-root, one broad discovery candidate.

## 5. Transfer scope

A successful direction or concept may be scoped to:

- one anchor;
- one world/prompt;
- one subject family;
- one model and basis family;
- global user memory.

**Proposed default:** local prompt/basis instance until held-out evidence justifies broader transport.

## 6. What should persist after a click?

A click may mean:

- the whole image is better;
- one detail is promising;
- continue this direction despite an imperfect image;
- retain subject/structure;
- lucky realization;
- least bad option.

**Input requested:** an annotated 15–20 decision trace recording why each image was chosen and what should persist.

## 7. Definition of a successful session

Rank these:

- exported/favorited final image;
- surprising image the user could not have prompted;
- coherent descendant chain;
- reusable direction/concept discovered;
- reduced prompt-writing burden;
- rapid convergence;
- broad exploration without collapse.

**Proposed default metrics:** first favorite/export, subjective surprise, perceptual slate diversity, branch regret, and held-out recast success.

## 8. Parent preservation controls

For a true-evolution treatment, which should be lockable?

```text
subject identity
composition/layout
palette
material/texture
text
specific region/mask
```

**Proposed default:** one edit-strength control plus optional subject and composition locks; avoid a full cockpit initially.

## 9. Naming learned objects

Options:

- never name automatically;
- neutral `Move 1` until promoted;
- machine-proposed name requiring confirmation;
- user names only;
- show exemplars instead of names.

**Proposed default:** neutral provisional names, then machine-proposed labels only after multiple exemplars.

## 10. Privacy and persistence

Decide whether preferred images, embeddings, and concept evidence remain:

- local to one browser/node;
- synchronized to a user account;
- exportable/importable;
- eligible for collaborative preference learning.

**Proposed default:** local/server-owned single-user evidence with explicit export; no collaborative use during Round 2.
