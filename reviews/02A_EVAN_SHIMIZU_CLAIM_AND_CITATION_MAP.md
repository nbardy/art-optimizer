# Evan Shimizu Claim and Citation Map

This document separates evidence from the UIST paper and thesis, design ideas discussed as future work, and Art Optimizer's own adaptations.

## Canonical sources

| Key | Source | Type | Primary use |
|---|---|---|---|
| `SHIMIZU-UIST` | [Design Adjectives](https://doi.org/10.1145/3379337.3415866) | peer-reviewed UIST paper | framework, implementation, study and case-study claims |
| `SHIMIZU-THESIS` | [CMU-CS-20-104](https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf) | doctoral thesis | equations, sampling modes, UI details, limitations, future work |
| `SHIMIZU-PROJECT` | [official project page](https://graphics.cs.cmu.edu/projects/design-adjectives/) | author project page | abstract, media, code, citation |
| `SHIMIZU-CODE` | [`ebshimizu/DesignAdjectives` at audited revision `cacfbbae`](https://github.com/ebshimizu/DesignAdjectives/tree/cacfbbaebe13b21c44e55738c2260a0e3312022c) | source code | system architecture and released implementation |

## Claim table

| Claim | Source | Safe wording | Avoid |
|---|---|---|---|
| The framework models subjective design concepts from examples | `SHIMIZU-UIST`, `SHIMIZU-THESIS` | “Design Adjectives learns a user-defined subjective function over a parameterized design space.” | “The system discovers universal semantic axes.” |
| The implementation uses GPR | `SHIMIZU-UIST`, `SHIMIZU-THESIS` §4.1 | “The domain-agnostic implementation fits Gaussian process regression to user scores.” | “All Design Adjectives implementations must use a GP.” |
| The examples are scored from 0 to 1 | `SHIMIZU-THESIS` §4.1 | “The evaluated implementation accepts scalar scores in [0,1].” | Attribute Art Optimizer's multi-choice likelihood to Shimizu. |
| Four sampling modes are provided | `SHIMIZU-THESIS` §4.2.1 | “Towards, Away, Similar Score, and Axis alter the sampler's acceptance criteria.” | “The four modes are a Bayesian acquisition function.” |
| Axis spans the learned score | `SHIMIZU-THESIS`, `SHIMIZU-CODE` | “Axis seeks examples at separated levels of the scalar adjective score.” | “Axis follows one learned linear direction through parameter space.” |
| Hover previews suggestions in the main view | `SHIMIZU-THESIS` Fig. 4.5 | “The evaluated interface lets users hover gallery thumbnails to render them in the main view.” | “Hover was treated as preference evidence.” |
| Press-and-hold preview appears in mobile discussion | `SHIMIZU-THESIS` Fig. 7.3 | “The thesis proposes press-and-hold full-size preview as a mobile adaptation.” | “A mobile press-and-hold interface was validated in the main user study.” |
| The framework was demonstrated in three domains | `SHIMIZU-UIST`, `SHIMIZU-PROJECT` | “Materials, fonts, and particle systems were demonstrated.” | “The framework was validated on diffusion-generated art.” |
| Users found exploration easier | `SHIMIZU-UIST`, `SHIMIZU-THESIS` | “The reported studies support usability and exploratory value in the tested domains.” | “Design Adjectives proves universally faster design.” |
| ARD length scales identify influential parameters | `SHIMIZU-THESIS` | “Length scales provide a model-based indication of parameter relevance.” | “ARD produces globally disentangled semantic controls.” |
| Posterior uncertainty drives the sampler | not established | “The GP supplies uncertainty, but the implementation principally uses its mean as the adjective score.” | “Design Adjectives already implements UCB/Thompson acquisition.” |

## Peer-reviewed citation

> Shimizu, Evan, Matthew Fisher, Sylvain Paris, James McCann, and Kayvon Fatahalian. “Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces.” In *Proceedings of the 33rd Annual ACM Symposium on User Interface Software and Technology*, 261–278, 2020. https://doi.org/10.1145/3379337.3415866

BibTeX:

```bibtex
@inproceedings{shimizu2020designadjectives,
  author    = {Shimizu, Evan and Fisher, Matthew and Paris, Sylvain and McCann, James and Fatahalian, Kayvon},
  title     = {Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces},
  booktitle = {Proceedings of the 33rd Annual ACM Symposium on User Interface Software and Technology},
  year      = {2020},
  pages     = {261--278},
  doi       = {10.1145/3379337.3415866}
}
```

## Thesis citation

> Shimizu, Evan. *Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools*. PhD thesis, Carnegie Mellon University, CMU-CS-20-104, 2020. https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf

Use the thesis for details not compactly stated in the UIST paper, including:

- the full framework decomposition;
- GPR equations and kernel details;
- rejection-sampler settings;
- sampling-mode acceptance criteria;
- hover and per-parameter tools;
- mobile and large-display future-interface concepts;
- the broader discussion of computational design assistants.

## Citation-ready paragraphs

### Local optimization ancestry

> Art Optimizer's branch-local interaction is directly informed by Shimizu et al.'s Design Adjectives framework, which learns a subjective function from user-scored examples and uses it to guide gallery sampling in high-dimensional parameterized spaces. The framework's Towards, Away, Similar Score, and Axis modes distinguish improvement, basin escape, iso-preference exploration, and coverage across scalar-score levels—roles that Art Optimizer adapts into candidate-policy experiments. Linear direction diagnostics are a separate Art Optimizer proposal.

### Interface ancestry

> The separation between preview and commitment follows the interaction pattern documented in the Design Adjectives interface: generated suggestions appear as thumbnails, while hovering renders a suggestion in the main design view. Art Optimizer makes the distinction explicit in state and event semantics so preview produces no preference update and only a click or tap changes the branch.

### Extension paragraph

> Art Optimizer differs from the evaluated Design Adjectives implementation by observing multi-choice decisions rather than absolute 0–1 scores, using posterior uncertainty during candidate selection, operating over a versioned image-generator control basis, and proposing a replayable family of explicit taste modes across worlds and sessions.

## Art Optimizer attribution boundary

| Component | Attribution |
|---|---|
| Learned subjective function over design parameters | Design Adjectives and earlier preference-learning work |
| Gallery-driven iterative refinement | Design Adjectives and related design-gallery literature |
| Towards/Away/Similar Score/Axis distinction | Design Adjectives |
| Full-size temporary hover preview | Design Adjectives interface precedent |
| Four corner candidates | Art Optimizer product choice |
| Anchor-as-outside-option likelihood | Art Optimizer synthesis with discrete-choice literature |
| Uncertainty-aware four-role planner | Art Optimizer synthesis with PBO/active learning |
| Replayable family of taste components | Art Optimizer extension informed by preference-learning and generative-recommender work |
| Diffusion/flow model codec | Art Optimizer architecture plus generative-control literature |

## Non-claims

Do not state that Shimizu et al. established:

- that four alternatives are optimal;
- that pairwise or multi-choice feedback is superior to scores;
- that their GP used uncertainty-aware BO acquisition;
- that the mobile swipe/hold proposal was the primary evaluated UI;
- that Design Adjectives learns stable global semantics in diffusion models;
- that the system supports persistent cross-session user profiles;
- that its evaluation generalizes without testing to open-ended generative art.
