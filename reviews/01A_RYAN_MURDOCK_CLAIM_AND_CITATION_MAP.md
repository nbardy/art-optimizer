# Ryan Murdock Claim and Citation Map

This companion document prevents a useful research prototype from being cited either too weakly (“just inspiration”) or too strongly (“validated production method”).

## Canonical sources

| Key | Source | Type | Use |
|---|---|---|---|
| `MURDOCK-GR` | [Generative Recommenders](https://rynmurdock.github.io/writing/generative_recommenders.html) | author essay | conceptual framing, Zahir method, qualitative loop |
| `MURDOCK-GR-CODE` | [`generative_recommender`](https://github.com/rynmurdock/generative_recommender) | prototype code | implementation details and scope |
| `MURDOCK-PP` | [`preference-prior`](https://github.com/rynmurdock/preference-prior) | prototype code | sequence-conditioned preference prior |
| `REN-2017` | [Personalized Image Aesthetics](https://openaccess.thecvf.com/content_ICCV_2017/html/Ren_Personalized_Image_Aesthetics_ICCV_2017_paper.html) | peer-reviewed paper | FLICKR-AES provenance |
| `HU-2008` | [Collaborative Filtering for Implicit Feedback Datasets](https://doi.org/10.1109/ICDM.2008.22) | peer-reviewed paper | weighted implicit-feedback factorization background |
| `CLIP-2021` | [Learning Transferable Visual Models From Natural Language Supervision](https://proceedings.mlr.press/v139/radford21a.html) | peer-reviewed paper | joint visual-language representation background |

## Claim table

| Claim | Support | Safe wording | Avoid |
|---|---|---|---|
| Preference history can condition generation | `MURDOCK-GR`, `MURDOCK-GR-CODE` | “Murdock demonstrates a prototype in which learned user representations are connected to visual generator conditioning.” | “Murdock proved generative recommenders outperform prompting.” |
| Collaborative factors are aligned with visual embeddings | `MURDOCK-GR`, `MURDOCK-GR-CODE` | “The prototype constrains/anchors learned item representations with CLIP image features so user factors become visually actionable.” | “The code is a definitive implementation of weighted ALS with a published objective.” |
| Feedback can be iterated through generation | `MURDOCK-GR` | “The essay reports qualitative iterations in which generated images are rated and added back to the interaction data.” | “The method converges to a user's true utility.” |
| FLICKR-AES provides overlapping personal ratings | `REN-2017`, `MURDOCK-GR` | “The experiment uses FLICKR-AES because it contains per-user image ratings suitable for personalized aesthetics.” | “FLICKR-AES is representative of all creative preference.” |
| A sequence of preferences can predict another preferred embedding | `MURDOCK-PP` | “The follow-up code experiments with predicting a held-out preferred-media embedding from a history sequence.” | “Preference Prior is a peer-reviewed state-of-the-art model.” |
| The work motivates persistent preference memory | `MURDOCK-GR`, `MURDOCK-PP` | “The work motivates retaining generative preference representations across interactions.” | “Murdock specifies Art Optimizer's multimodal atlas.” |
| Multiple persistent modes are needed | Art Optimizer interpretation | “We extend the work by representing taste as multiple coherent components rather than one average vector.” | Attribute the mixture-atlas algorithm directly to Murdock. |

## Source-specific notes

### `MURDOCK-GR`

Cite this source for:

- the distinction between prompted generation and interaction-conditioned generation;
- artist-as-curator/explorer framing;
- the Zahir collaborative-filtering plus visual-embedding bridge;
- the qualitative generated-feedback loop;
- the explicit statement that scaling is beyond the essay's scope;
- the later preference-prior direction described in the essay.

Do not cite it as a formal controlled user study or benchmark paper.

Suggested reference:

> Murdock, Ryn. “Generative Recommenders.” 5 April 2024. https://rynmurdock.github.io/writing/generative_recommenders.html

### `MURDOCK-GR-CODE`

The repository's workflow is explicit: construct the FLICKR-AES interaction matrix, compute CLIP image embeddings, add ratings for a target user, optimize user embeddings, and use the result through Kandinsky or IP-Adapter-style conditioning.

The factor-learning script uses alternating censored least-squares updates and image-feature anchoring. Treat it as research code. Do not retrofit a more polished objective and imply that exact objective appears in the source.

Suggested reference:

> Murdock, Ryn. `generative_recommender`. GitHub repository. https://github.com/rynmurdock/generative_recommender

### `MURDOCK-PP`

The code adapts a text-to-image prior architecture toward a history-to-held-out-image-embedding problem. Inputs include preferred-image embeddings, scores, prompt embeddings, and experimental demographic features. The project is directly relevant to sequence-conditioned preference, but no claim in Art Optimizer should exceed the evaluation published with that repository.

Suggested reference:

> Murdock, Ryn. `preference-prior`. GitHub repository. https://github.com/rynmurdock/preference-prior

## Citation-ready paragraphs

### Related-work paragraph

> Murdock's *Generative Recommenders* prototype explores a shift from retrieving existing media to conditioning generation on collaborative interaction histories. The prototype aligns learned item factors with CLIP image embeddings so that a learned user representation can be passed into an image-generation stack, while a later `preference-prior` project experiments with predicting a held-out preferred-media embedding from a sequence of preferred examples. These projects are released research prototypes rather than production-scale evaluations, but they directly motivate Art Optimizer's persistent generative preference layer.

### Extension paragraph

> Art Optimizer extends this direction in two ways. First, it stores a multimodal atlas of coherent taste components rather than a single averaged user vector. Second, it separates slowly evolving persistent memory from the fast branch-local discrete-choice posterior used to select the next quartet. This extension is an Art Optimizer design decision, not a claim about the algorithm implemented by Murdock.

### Limitations paragraph

> The original generative-recommender prototype does not define an uncertainty-aware next-query policy, exposure correction, a branch-local optimizer, or a controlled evaluation of convergence. Art Optimizer therefore uses Murdock's representation bridge as a prior/memory concept and relies on separate preference-learning and acquisition literature for online candidate selection.

## Non-claims to preserve

Art Optimizer should not state that:

- Murdock invented all generative recommendation;
- the Zahir prototype was peer reviewed;
- the prototype was evaluated at production scale;
- one CLIP-space user vector is sufficient for long-term taste;
- matrix factorization is the current Art Optimizer online learner;
- user demographics are required or endorsed by Art Optimizer;
- qualitative steering proves causal preference learning;
- collaborative factors transfer unchanged to every generator or model codec.

## Art Optimizer attribution boundary

| Component | Attribution |
|---|---|
| Interaction history as generative conditioning | strongly motivated by Murdock |
| CLIP-aligned collaborative user/item representation | Murdock prototype, with collaborative-filtering and CLIP antecedents |
| Sequence-conditioned preference prior | Murdock follow-up prototype |
| Multimodal persistent atlas | Art Optimizer extension |
| Event-specific evidence weights | Art Optimizer design |
| Branch-local multinomial learner | preference-learning literature + Art Optimizer implementation |
| Four-role candidate acquisition | Art Optimizer synthesis |
| Exact replay and branch forest | Art Optimizer product/state architecture |
