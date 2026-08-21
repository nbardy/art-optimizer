# Research Review 1/5: Ryan Murdock's Generative Recommenders and Preference Priors

**Primary objects reviewed**

- Ryn Murdock, [“Generative Recommenders”](https://rynmurdock.github.io/writing/generative_recommenders.html), 2024.
- Murdock, [`generative_recommender`](https://github.com/rynmurdock/generative_recommender), source prototype.
- Murdock, [`preference-prior`](https://github.com/rynmurdock/preference-prior), follow-up research code.

**Source status:** author research essay plus released prototypes; not treated here as a peer-reviewed empirical paper.

## 1. Review question

What is the durable research contribution of Murdock's work for a system that does not merely retrieve images, but generates new images from a user's evolving interaction history?

The most important answer is not a particular matrix-factorization implementation. It is the shift in object being learned:

```text
traditional recommender
    user history -> rank existing items

generative recommender
    user history -> condition the creation of a new item
```

That shift is central to Art Optimizer. The user does not need to perfectly verbalize the desired image, and the system does not need the desired image to already exist in a catalog. Interaction history itself becomes a generative condition.

## 2. The Zahir / Generative Recommenders thesis

Murdock asks what visual generation looks like when it is conditioned on a person's interactions and the interactions of related users rather than on text alone. The essay frames this as a change in creative role: the person can operate as curator and explorer, repeatedly recognizing compelling outputs without first having to name the visual relationships that make them compelling.

This is an important distinction between **description** and **preference**:

- A prompt expresses what the user can state.
- A preference representation attempts to capture what the user repeatedly selects.
- The two overlap, but neither contains the other.

A user may be able to request “an architectural landscape at night” yet repeatedly favor compositions with asymmetrical masses, small warm lights, dense atmospheric depth, and an unusually low horizon. Those relationships may be stable enough to learn even if the user never articulates them.

### 2.1 Conceptual model

Let \(R\in\mathbb{R}^{U\times I}\) be a sparse user-item interaction matrix, with user factors \(P\in\mathbb{R}^{U\times d}\), item factors \(Q\in\mathbb{R}^{I\times d}\), and image features \(\phi_i\) from a vision-language embedding model such as CLIP.

A clean mathematical abstraction of the essay's idea is:

\[
\min_{P,Q,A}
\sum_{u,i} c_{ui}\left(r_{ui}-p_u^\top q_i\right)^2
+\lambda_P\lVert P\rVert_F^2
+\lambda_Q\lVert Q\rVert_F^2
+\gamma\sum_i\lVert q_i-A\phi_i\rVert_2^2.
\]

The first term is collaborative preference reconstruction. The final term aligns item factors with a generative visual representation. Once this alignment exists, a user vector can be interpreted in, or transported into, a space that conditions an image generator.

This equation is a faithful formalization of the research direction, **not a claim that the released prototype implements this exact regularized objective line-for-line**. The repository uses an experimental alternating/censored least-squares procedure and anchors learned item features to image embeddings by augmenting the factorization problem with image-identity constraints. That implementation is evidence of the mechanism, not a polished canonical algorithm.

### 2.2 Why CLIP alignment matters

Ordinary collaborative factors are only defined up to transformations that preserve their dot products. A user vector from an unconstrained factorization is useful for ranking within that factorization but has no guaranteed meaning to a generator.

Aligning items with a joint image-text space provides a bridge:

\[
p_u \longrightarrow z_u \longrightarrow G(z_u, c),
\]

where \(z_u\) is a user-conditioned visual embedding and \(c\) may include text or other conditions. Murdock's prototype demonstrates this idea using CLIP image embeddings and generation through Kandinsky or IP-Adapter-like conditioning.

The contribution is therefore a **representation bridge**:

```text
collaborative interactions
    -> user representation
    -> visual/generative embedding
    -> novel media
```

That bridge is more important to Art Optimizer than the particular recommender loss used in the first prototype.

## 3. Evidence and implementation scope

The essay uses [FLICKR-AES](https://openaccess.thecvf.com/content_ICCV_2017/html/Ren_Personalized_Image_Aesthetics_ICCV_2017_paper.html), a dataset associated with *Personalized Image Aesthetics*, because it contains ratings from overlapping users rather than only one aggregate aesthetic score. The prototype workflow is:

1. build a user-image interaction matrix;
2. compute CLIP image embeddings;
3. add a target user's ratings;
4. optimize user and item embeddings;
5. use a learned user embedding to condition visual generation.

The essay reports qualitative iterative experiments in which generated images are rated and fed back into the interaction data. Murdock describes the loop as moving toward regions he finds compelling.

This supports a limited but valuable claim:

> A collaborative representation constrained by visual embeddings can be made generatively actionable, and repeated feedback can qualitatively steer generation.

It does **not** establish:

- large-scale recommendation quality;
- convergence guarantees;
- superiority to modern preference-learning baselines;
- calibrated uncertainty;
- robust causal effects of each feedback event;
- long-term user satisfaction;
- or production behavior under exposure bias.

The essay explicitly presents scaling as outside its scope, and the repository describes itself as experimental.

## 4. The later Preference Prior direction

The [`preference-prior`](https://github.com/rynmurdock/preference-prior) project moves beyond one static collaborative vector. Its README describes fine-tuning an ECLIPSE-style prior from:

```text
text embedding -> image embedding
```

toward:

```text
sequence of preferred media embeddings -> held-out preferred image embedding
```

The released code constructs sequences of preferred images, embeds them, optionally uses scores and text embeddings, and trains a prior to predict a target image embedding. The model also experiments with demographic conditioning and dropout of history elements.

This is closer to the persistent-memory problem Art Optimizer actually has. Preference is not only a fixed location in embedding space; it may depend on:

- which interests were recently active;
- the order in which examples were encountered;
- the current prompt or project;
- score strength;
- and the subset of a person's history relevant to the current context.

A sequence prior can model:

\[
p(z_{t+1}\mid z_{1:t}, s_{1:t}, c),
\]

instead of reducing history to:

\[
\bar z = \frac{1}{t}\sum_{i=1}^t z_i.
\]

The latter average is cheap but destructive when the user has multiple coherent tastes.

## 5. The central extension: a persistent **set** of priors

Art Optimizer should not interpret Murdock's work as a mandate to keep one permanent user vector. The useful extension is a persistent, evolving atlas:

\[
\mathcal P_u
=
\left\{
P_k=(\alpha_k,\mu_k,\Sigma_k,N_k,t_k,E_k)
\right\}_{k=1}^{K}.
\]

Each component represents one coherent mode of taste:

- \(\alpha_k\): proposal mass or current relevance;
- \(\mu_k\): feature-space center;
- \(\Sigma_k\): tolerated variation and uncertainty;
- \(N_k\): supporting evidence mass;
- \(t_k\): recency/last activation;
- \(E_k\): replayable exemplars.

This avoids the “average taste” failure mode. A user can separately prefer:

- monochrome brutalist architecture;
- colorful biomorphic illustration;
- dense generative line systems;
- intimate cinematic portraits.

A single centroid may fall between them and correspond to nothing the person actually likes.

### 5.1 Contextual activation

At world creation, the system should infer responsibilities:

\[
r_k
= P(k\mid I_t,c_t,h_t),
\qquad
\sum_k r_k = 1,
\]

then use a context-dependent prior mixture:

\[
p(w_0)
=
\sum_k r_k\,\mathcal N(\mu_k,\Sigma_k).
\]

The active branch posterior is allowed to move quickly; the atlas moves slowly.

```text
persistent atlas
    broad, multimodal, durable

session/branch posterior
    narrow, fast, reversible
```

That separation is the strongest practical synthesis of Murdock's direction.

## 6. Event semantics implied by the review

Different interactions should contribute differently to persistent memory.

| Event | Interpretation | Persistent effect |
|---|---|---:|
| Candidate commit | “Continue from this route” | weak positive |
| Favorite | “This belongs in my durable taste” | strong positive |
| Revisit old branch | “This retained value over time” | moderate positive |
| Export/use | “This survived reflection and became an artifact” | strongest positive |
| Reroll | “None of these local proposals beat the anchor” | normally none |
| New world | “Change stochastic basin” | none; preserve atlas |
| Unfavorite | retract favorite evidence | not a dislike |

This distinction prevents navigation from overwhelming long-term preference. A selected image can be a promising intermediate step rather than a final aesthetic endorsement.

## 7. What Murdock contributes to Art Optimizer

### Directly adopted

1. **Preference can condition generation, not only retrieval.**
2. **Interaction history contains visual information that prompts omit.**
3. **A shared visual embedding can connect recommender representations to generators.**
4. **Generated outputs can be rated and returned to the preference model.**
5. **A user's role can be curator/explorer rather than prompt engineer.**
6. **Sequence-conditioned preference representations are a promising successor to static factorization.**

### Extended by Art Optimizer

1. one vector becomes a multimodal persistent atlas;
2. persistent memory is separated from a branch-local posterior;
3. selection, favorite, reroll, reset, revisit, and export have different semantics;
4. every exemplar is replayable and tied to model/control revisions;
5. the next query is chosen by an uncertainty- and diversity-aware policy;
6. exposure is logged so unshown candidates are not treated as rejected;
7. model-specific action coordinates are never presumed transferable across control bases.

### Not inherited

Art Optimizer should not copy the original prototype as its online learner. Sparse matrix factorization is most valuable once many users share rated items. In Art Optimizer, generated images are often unique and branch-specific, so the initial online loop is better modeled with content features and discrete choice. Collaborative or sequence priors can initialize or regularize that loop later.

## 8. Methodological limitations

### 8.1 Sparse shared items

Classical collaborative filtering benefits when users overlap on a catalog of items. Generated images produce a rapidly expanding, mostly unique catalog. Similarity through image embeddings helps, but it changes the problem from ordinary collaborative filtering toward content-conditioned preference modeling.

### 8.2 One-vector compression

A static user embedding can blur incompatible interests. The later preference-prior project helps, but a production system still needs mixture structure or retrieval over exemplars.

### 8.3 No explicit acquisition policy

The work learns a representation but does not fully specify which four images should be generated next to maximize both user value and information gain. Art Optimizer needs a planner, not only a user embedding.

### 8.4 Exposure and position bias

A user can only select what was generated and displayed. Without logging proposal policies, rank, visibility, and availability, historical interactions can make the system learn its own exposure policy rather than the person's underlying preference.

### 8.5 Preference drift and inspiration

The user may discover a new interest because the system showed an unexpected image. This is not merely noise around a fixed utility function. Persistent memory needs dormant modes, contextual activation, and reserved outside-prior exploration.

### 8.6 Evaluation

The prototypes are highly suggestive but do not provide the controlled evaluation needed to choose clustering thresholds, sequence architecture, update weights, or candidate policies for Art Optimizer.

## 9. Research implications

The Murdock-inspired research program should be evaluated in layers.

### Layer A: persistent representations

Compare:

- weighted mean embedding;
- online mixture/cluster atlas;
- exemplar retrieval;
- sequence-conditioned preference prior;
- collaborative-plus-content prior.

Metrics:

- held-out favorite retrieval;
- calibration of mode responsibilities;
- cross-session return prediction;
- diversity among high-scoring modes;
- resistance to accidental-click drift.

### Layer B: generative conditioning

Compare:

- prompt embedding addition;
- reference-image conditioning;
- positive/negative attention exemplars;
- model-specific adapter heads;
- learned image-feature-to-action transport.

Metrics:

- preference lift over prompt-only;
- identity/composition preservation;
- cross-seed transfer;
- cross-model transfer only when explicitly trained;
- novelty without mode collapse.

### Layer C: online interaction

Measure whether atlas initialization reduces:

- rounds to first favorite;
- rounds to first export;
- reroll rate;
- abandonment after New world;
- and repeated rediscovery of the same taste mode.

## 10. Citation-safe conclusion

The strongest citation-safe statement is:

> Murdock's *Generative Recommenders* work demonstrates, through an essay and released prototypes, how collaborative and sequence-based preference representations can be aligned with visual embeddings and used to condition novel image generation. Art Optimizer extends this direction with an evolving multimodal taste atlas, branch-local discrete-choice learning, explicit interaction semantics, and uncertainty-aware candidate selection.

The project should not say that Murdock established a production-scale recommender, proved convergence, or validated Art Optimizer's atlas algorithm. The value of the work is its unusually direct formulation of the generative-preference problem and its concrete representation bridge.

## References

- Ryn Murdock. [“Generative Recommenders.”](https://rynmurdock.github.io/writing/generative_recommenders.html) 2024.
- Ryn Murdock. [`generative_recommender`](https://github.com/rynmurdock/generative_recommender). Source code.
- Ryn Murdock. [`preference-prior`](https://github.com/rynmurdock/preference-prior). Source code.
- Yifan Hu, Yehuda Koren, and Chris Volinsky. [“Collaborative Filtering for Implicit Feedback Datasets.”](https://doi.org/10.1109/ICDM.2008.22) ICDM, 2008.
- Jian Ren, Xiaohui Shen, Zhe Lin, Radomír Měch, and David J. Foran. [“Personalized Image Aesthetics.”](https://openaccess.thecvf.com/content_ICCV_2017/html/Ren_Personalized_Image_Aesthetics_ICCV_2017_paper.html) ICCV, 2017.
- Alec Radford et al. [“Learning Transferable Visual Models From Natural Language Supervision.”](https://proceedings.mlr.press/v139/radford21a.html) ICML, 2021.
- Wenjie Wang, Xinyu Lin, Fuli Feng, Xiangnan He, and Tat-Seng Chua. [“Generative Recommendation: Towards Next-generation Recommender Paradigm.”](https://arxiv.org/abs/2304.03516) 2023/2024 manuscript.
- Maitreya Patel, Changhoon Kim, Sheng Cheng, Chitta Baral, and Yezhou Yang. [“ECLIPSE: A Resource-Efficient Text-to-Image Prior for Image Generations.”](https://arxiv.org/abs/2312.04655) 2023.
