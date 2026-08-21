# Research Review 5/5: Interactive Generative Search Systems

## 1. Review question

What interaction pattern best lets a person navigate a generative image space when:

- the target is partly tacit;
- the generator has many coupled degrees of freedom;
- each candidate costs compute;
- each judgment costs attention;
- the user's preference may change after seeing new work;
- and the user must retain authorship rather than become a passive engagement signal?

No single prior system answers the full question. The relevant lineage includes interactive evolutionary computation, model-guided design galleries, active preference learning, latent-space swipe interfaces, feedback-conditioned diffusion, adapter-merging tools, and recent multi-choice Bayesian image optimization.

## 2. A comparative frame

Interactive generative systems differ along at least eight dimensions:

1. **User signal:** ratings, pairwise choices, multi-choice, positive/negative sets, direct sliders.
2. **Search representation:** hand-authored parameters, GAN latents, attention transforms, adapters, references, prompt embeddings.
3. **Query policy:** random evolution, local perturbation, active learning, bandit, Bayesian optimization.
4. **Objective:** target matching, subjective preference, broad discovery, final refinement.
5. **State horizon:** one round, one session, persistent user memory.
6. **Agency:** whether the user can preview, reject all, restore, branch, or directly manipulate.
7. **Recovery:** whether a mistaken choice is reversible.
8. **Evaluation:** synthetic objective, target image, user preference, workflow quality, or engagement.

Art Optimizer should be understood as a synthesis across these dimensions, not as an isolated “RL image app.”

## 3. Interactive evolutionary computation

[Takagi's survey of Interactive Evolutionary Computation](https://doi.org/10.1109/5.949485) reviews systems in which a human supplies the fitness signal for evolutionary search. The broad pattern is:

```text
population
    -> human evaluation
    -> selection/recombination/mutation
    -> new population
```

IEC has been applied to graphics, music, industrial design, data mining, and other domains where an analytic objective is difficult to specify.

### 3.1 Durable contribution

IEC established that human subjective evaluation can close the optimization loop. The user need not write a differentiable reward; recognition can be enough.

### 3.2 Persistent problem: user fatigue

The same human remains the bottleneck. Large populations, numeric ratings, and many generations can exhaust attention. A system that shows more images can obtain more labels while making the actual experience worse.

This implies several design constraints for Art Optimizer:

- small slates;
- low-friction choices;
- visible progress;
- ability to keep the current design;
- strong reversibility;
- uncertainty-aware use of each judgment;
- no hidden pressure to continue interacting.

The four-image interaction is best understood as a fatigue-conscious IEC descendant with a probabilistic learner rather than a conventional genetic population.

## 4. Design galleries before learned preference

Classic design-gallery systems make a parameterized space browsable through generated examples rather than exposing only sliders. Gallery views exploit human visual recognition and comparison.

Their core insight remains valid:

> The system should translate a difficult high-dimensional control problem into a sequence of visual judgments.

But static or uniformly sampled galleries do not learn which region matters to the current user. They can spend most of the screen budget on irrelevant variation.

## 5. Active preference learning for graphics

[Brochu, de Freitas, and Ghosh](https://papers.nips.cc/paper_files/paper/2007/hash/b6a1085a27ab7bff7550f8a3bd017df8-Abstract.html) formulate active preference learning from discrete-choice observations and demonstrate it on graphics/material design parameters. The system chooses comparisons intended to improve its model efficiently.

[Brochu, Brochu, and de Freitas](https://doi.org/10.2312/SCA/SCA10/103-112) extend Bayesian interactive optimization to procedural animation design.

These works add an essential layer to gallery interaction:

```text
not merely generate alternatives
but choose alternatives that make the next human judgment valuable
```

Art Optimizer inherits this view, but its query is a slate with an anchor rather than one pair.

## 6. Design Adjectives

[Design Adjectives](https://doi.org/10.1145/3379337.3415866) combines a learned subjective function with a visual gallery and low-level parameter tools. It offers Towards, Away, Similar Score, and Axis exploration modes.

Its distinctive HCI contribution is the separation between:

- visual discovery through generated suggestions;
- temporary full-context preview;
- explicit ratings/commitment;
- detailed direct manipulation.

Art Optimizer's one-canvas/four-corner interaction is closest to this lineage. It preserves one authoritative current design and treats alternatives as possible descendants rather than unrelated feed items.

## 7. Sequential Gallery

[Sequential Gallery](https://doi.org/10.1145/3386569.3392444) reduces high-dimensional visual optimization to a sequence of two-dimensional plane-search tasks. The user chooses preferred examples in each gallery, and the system updates the search trajectory.

Its strongest lesson is not the exact plane-search algorithm. It is the co-design of optimization and judgment:

> A query should be geometrically informative and visually answerable.

A mathematically optimal batch of four nearly identical images may be impossible to compare. Four extremely unrelated images may be easy to distinguish but teach little about a local preference boundary. Candidate design must account for human discriminability.

## 8. SwipeGANSpace

[SwipeGANSpace](https://arxiv.org/abs/2404.19693) creates PCA-based StyleGAN subspaces, gathers swipe comparisons, models preference with preferential Bayesian optimization, and uses a multi-armed bandit to decide which latent dimension to explore.

It is a direct ancestor of a “browse, choose, learn a direction” product.

### 8.1 Contributions relevant to Art Optimizer

- extremely lightweight comparison gestures;
- latent dimensions selected adaptively;
- preference learning over generator controls;
- evidence that displayed novelty can inspire a user and alter preference;
- acknowledgement that preference is dynamic rather than a fixed hidden target.

### 8.2 Boundaries

- one-dimensional dimension selection can miss compositional direction mixtures;
- PCA directions are model/domain-specific;
- swipe semantics can collapse “not now,” “worse,” and “wrong attribute” into one signal;
- the interaction does not by itself provide persistent multi-interest memory;
- a left/right feed lacks Art Optimizer's explicit committed anchor and branch history.

## 9. FABRIC

[FABRIC](https://doi.org/10.1007/978-3-031-91907-7_23) accepts positive and negative feedback images and steers future diffusion generations through attention-based reference conditioning without model training.

This system occupies a different layer than a preference optimizer:

```text
interaction
    user marks images as positive/negative

conditioning
    feedback-image features enter attention

sampling
    generator produces new images
```

The mechanism is highly relevant, but FABRIC does not fully solve:

- which images to show next;
- how to distinguish transient from persistent taste;
- how to branch and restore;
- how to infer exposure;
- or how to combine feedback with multiple control quantities.

Art Optimizer can use a FABRIC-like mechanism as one renderer codec while retaining its own event semantics and acquisition policy.

## 10. GimmBO

[GimmBO](https://arxiv.org/abs/2601.18585) treats weights over a bank of image-generation adapters as a continuous design space and uses preferential Bayesian optimization to help users search it. The paper is motivated by the impracticality of manually tuning mixtures from even twenty to thirty adapters.

Its interactive significance is substantial:

- it searches explicit reusable generator modules;
- the action has quantities the user could later expose as sliders;
- sparsity is treated as a real prior;
- the optimizer is tailored to the geometry of the application;
- simulated and human evaluation compare against manual/optimization baselines.

GimmBO is closer to **customizing a model mixture** than to persistent open-ended browsing across arbitrary worlds. Art Optimizer can adopt adapter blocks without inheriting its entire UI or objective.

## 11. MultiBO

[MultiBO](https://arxiv.org/abs/2602.02388) formalizes multi-choice preferential Bayesian optimization for image generation after language prompting reaches its limit. It generates several alternatives around a current result, obtains a human choice, updates a preference model, and repeats in a constrained attention-transformation space.

### 11.1 Strong overlap

- one current image;
- several alternatives per round;
- multi-choice rather than only pairwise feedback;
- compact generator intervention space;
- uncertainty-aware optimization;
- user-query efficiency;
- a human study with multiple baselines.

### 11.2 Important difference

MultiBO begins from an implicit target image \(x^*\) in the user's mind. Progress means approaching that target.

Art Optimizer often has no fixed \(x^*\). The user may be asking:

> Show me what this could become.

This is an **open-ended discovery** problem. Inspiration can modify the goal, and a branch can be valuable even if it does not approach the initial concept.

This difference changes evaluation. Target similarity is appropriate for MultiBO; Art Optimizer also needs measures of discovery, agency, diversity, retention of interesting alternatives, and final artifact use.

## 12. System comparison

| System | Signal | Control space | Query policy | Persistent memory | Anchor / restore | Main objective |
|---|---|---|---|---|---|---|
| IEC | ratings/selections | genotype/parameters | evolutionary | usually no | varies | subjective fitness |
| Active preference graphics | pairwise choice | explicit parameters | active/Bayesian | session | limited | preference optimization |
| Design Adjectives | scalar scores | explicit parameters | GP-guided rejection | adjective/session | current design + gallery | subjective concept exploration |
| Sequential Gallery | gallery choice | sequential planes | line/plane search | session | trajectory | visual design optimization |
| SwipeGANSpace | swipes | PCA GAN directions | PBO + bandit | session | weak | preferred image search |
| FABRIC | positive/negative images | attention references | feedback conditioning | feedback sets | limited | iterative personalization |
| GimmBO | preferences | adapter weights | specialized PBO | session | current mixture | adapter merging |
| MultiBO | multi-choice | attention transforms | multi-choice PBO | session | current result | implicit target alignment |
| Art Optimizer | commit, reroll, favorite, restore | versioned hybrid codec | four-role preferential slate planner | multimodal cross-session atlas | explicit anchor + branch forest | open-ended evolution and refinement |

This table identifies Art Optimizer's synthesis. It should not be used to make a priority claim that no prior system ever combined any pair of these features.

## 13. Interaction primitives as a language

A usable creative system needs more than a positive/negative label. Art Optimizer defines a small action language.

### Preview

> Let me inspect this at full context without changing anything.

No preference or branch update.

### Commit

> Continue the design process from this exact state.

Strong branch-local choice; weak persistent evidence.

### Reroll

> Keep the current design; none of the judgeable alternatives should replace it.

Weak local outside-option evidence when exposure is sufficient.

### Favorite

> Remember this as part of my durable taste, whether or not I continue from it.

Strong persistent evidence.

### New world

> Change the stochastic basin while retaining broader taste.

Local reset; no negative label.

### Restore

> Return to this exact prior checkpoint and fork again.

Exact state recovery; moderate persistent revisit evidence.

This vocabulary is richer than swipe left/right while remaining small enough to learn.

## 14. Why one current image matters

A scrolling recommender feed asks:

> Which item do you like?

Art Optimizer asks:

> Which possible change is worth making to this design?

The current image supplies:

- a visual reference;
- an outside option;
- continuity of authorship;
- a branch identity;
- a baseline for causal comparison;
- a meaningful reroll choice.

Without the anchor, a user may choose the best among four bad images and accidentally move the search. With the anchor, “none” is represented by keeping the current state.

## 15. Why four candidates is plausible—and unproven

Four alternatives offer:

- enough choice to support different acquisition roles;
- a natural two-by-two/corner spatial mapping;
- one multi-choice observation per round;
- lower rendering cost than large galleries;
- manageable visual attention.

But four also creates risks:

- candidate thumbnails may be too small;
- full-size preview is serial and relies on visual memory;
- corner overlays can occlude the artwork;
- users may choose based on position or first-ready bias;
- more alternatives might improve discovery for cheap models;
- fewer alternatives might reduce fatigue on mobile.

Therefore “four” is an explicit product hypothesis to A/B test against at least two and six alternatives.

## 16. Candidate-role design

The four internal roles express different purposes:

1. **Best local:** likely progress from the anchor.
2. **Diverse posterior:** another plausible interpretation of current preference.
3. **Informative probe:** uncertain, chosen to improve the model.
4. **Controlled surprise:** a farther or alternate-mode candidate.

The roles should not be shown as labels in v0. Labels could bias judgment (“this is the smart option,” “this is random”). They remain metadata for analysis and ablation.

A system should compare this policy against:

- top-four exploitation;
- four random local perturbations;
- four Thompson samples;
- local/global mixtures;
- and diversity-only slates.

## 17. Agency and recovery

Creative optimization is particularly vulnerable to accidental overcommitment. The reviewed systems vary widely in recoverability.

Art Optimizer's branch forest should preserve:

```text
root
 └─ A
    ├─ B
    │  └─ C
    └─ D
       └─ E
```

Restoring A and selecting D does not destroy B and C. This has three benefits:

1. experimentation feels safer;
2. reversals reveal stable preference;
3. offline analysis retains counterfactual branch structure.

History should contain committed states, not every impression. Otherwise it becomes a noisy audit log rather than a creative memory.

## 18. Open-endedness and diversity

A pure optimizer tends to collapse around predicted utility. A pure novelty system may generate endless interesting images without helping the user finish anything.

Art Optimizer needs both:

\[
J(S)
=\text{preference progress}
+\lambda_N\text{novelty}
+\lambda_I\text{information}
-\lambda_F\text{fatigue}
-\lambda_C\text{catastrophic jumps}.
\]

The coefficients need not be solved as one RL reward in v0. Candidate roles, outside-prior mass, trust-region adaptation, and explicit New world provide interpretable controls over the tradeoff.

## 19. What the reviewed systems do not jointly solve

Across the literature, the following combined problem remains open:

- persistent multimodal taste across sessions;
- fast local preference updates;
- open-ended goal evolution;
- a hybrid diffusion/flow control manifold;
- replayable model and stochastic state;
- uncertainty-aware four-candidate slate selection;
- explicit preview/commit/favorite/reset semantics;
- recoverable branch history;
- and evaluation that rewards creative value rather than engagement.

This is a legitimate Art Optimizer research agenda. It is not license to claim every component as novel or solved.

## 20. Product conclusions

### Keep in the primary UI

- one committed image;
- four stable candidate locations;
- full-size temporary preview;
- explicit commit;
- reroll/keep anchor;
- favorite separate from navigation;
- New world;
- recent exact history.

### Add next

- Export with provenance as the strongest durable positive signal;
- “render broken / not judgeable” as a zero-preference system-quality action;
- a visible loading/failure state per slot;
- lightweight keyboard/touch help.

### Experiment before adding

- generic dislike/thumbs-down;
- reason codes after repeated rerolls;
- explicit surprise level;
- two/four/six candidate counts;
- corner overlays versus a two-by-two grid;
- learned direction chips and sliders;
- “another side of my taste” world resets.

### Avoid

- hidden dwell-time rewards;
- endless feed mechanics;
- streaks or engagement gamification;
- treating New world as rejection;
- learning from unshown candidates;
- automatically fine-tuning the generator after every click;
- forcing commitment because one candidate must win.

## 21. Citation-safe conclusion

Interactive generative-search research supports a progression from human-scored evolutionary populations, through model-guided parameter galleries and active preference learning, to modern feedback-conditioned and Bayesian-optimized image generators. Art Optimizer combines these lines around one evolving design, a multi-choice outside-option interaction, persistent multimodal memory, and replayable branching. Its distinctive value must be established through comparative experiments on agency, progress, discovery, and fatigue—not asserted from architecture alone.

## References

- Hideyuki Takagi. [“Interactive Evolutionary Computation: Fusion of the Capabilities of EC Optimization and Human Evaluation.”](https://doi.org/10.1109/5.949485) *Proceedings of the IEEE* 89(9), 2001.
- Eric Brochu, Nando de Freitas, and Abhijeet Ghosh. [“Active Preference Learning with Discrete Choice Data.”](https://papers.nips.cc/paper_files/paper/2007/hash/b6a1085a27ab7bff7550f8a3bd017df8-Abstract.html) NeurIPS, 2007.
- Eric Brochu, Tyson Brochu, and Nando de Freitas. [“A Bayesian Interactive Optimization Approach to Procedural Animation Design.”](https://doi.org/10.2312/SCA/SCA10/103-112) SCA, 2010.
- Evan Shimizu et al. [“Design Adjectives.”](https://doi.org/10.1145/3379337.3415866) UIST, 2020.
- Yuki Koyama, Issei Sato, and Masataka Goto. [“Sequential Gallery for Interactive Visual Design Optimization.”](https://doi.org/10.1145/3386569.3392444) ACM TOG, 2020.
- Yuto Nakashima, Mingzhe Yang, and Yukino Baba. [“SwipeGANSpace.”](https://arxiv.org/abs/2404.19693) 2024.
- Dimitri von Rütte et al. [“FABRIC.”](https://doi.org/10.1007/978-3-031-91907-7_23) ECCV 2024 Workshops.
- Chenxi Liu, Selena Ling, and Alec Jacobson. [“GimmBO.”](https://arxiv.org/abs/2601.18585) 2026.
- Rajalaxmi Rajagopalan et al. [“Personalized Image Generation via Human-in-the-loop Bayesian Optimization.”](https://arxiv.org/abs/2602.02388) 2026.
