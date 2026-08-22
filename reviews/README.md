# Art Optimizer Review Corpus

**Status:** internal research and design review  
**Review date:** 2026-08-22  
**Scope:** persistent generative preference, interactive subjective optimization, image-model control spaces, and the product semantics of Art Optimizer

This directory separates formal research reviews from product synthesis and design decisions. The goal is not to decorate the project with citations after the fact. The goal is to make clear:

1. what prior work actually established;
2. which parts Art Optimizer directly adopts;
3. which parts are extensions or hypotheses;
4. what the current product must test before making stronger claims.

## Five research reviews

1. [Ryan Murdock: Generative Recommenders and Preference Priors](01_RYAN_MURDOCK_GENERATIVE_RECOMMENDERS.md)  
   Reviews the Zahir/generative-recommender essay, the CLIP-aligned collaborative-filtering prototype, and the later sequence-conditioned preference-prior project.

2. [Evan Shimizu: Design Adjectives](02_EVAN_SHIMIZU_DESIGN_ADJECTIVES.md)  
   Reviews the UIST 2020 paper, the CMU thesis, the source repository, Gaussian-process subjective-function modeling, guided sampling modes, gallery interaction, and hover visualization.

3. [Preference Learning and Preferential Bayesian Optimization](03_PREFERENCE_LEARNING_AND_PREFERENTIAL_BO.md)  
   Reviews Gaussian-process preference learning, active discrete-choice learning, preferential Bayesian optimization, multi-choice likelihoods, uncertainty, and nonstationary preferences.

4. [Generative Control Spaces and Learned Directions](04_GENERATIVE_CONTROL_SPACES_AND_DIRECTIONS.md)  
   Reviews latent and activation directions, text-guided directions, attention/reference conditioning, adapter mixtures, initial-noise controls, and the requirements for a valid model codec.

5. [Interactive Generative Search Systems](05_INTERACTIVE_GENERATIVE_SEARCH_SYSTEMS.md)  
   Compares Design Adjectives, interactive evolutionary computation, active preference tools, Sequential Gallery, SwipeGANSpace, FABRIC, GimmBO, and MultiBO as interactive systems rather than isolated algorithms.

## Companion reviews and design explorations

- [Murdock claim and citation map](01A_RYAN_MURDOCK_CLAIM_AND_CITATION_MAP.md)
- [Shimizu claim and citation map](02A_EVAN_SHIMIZU_CLAIM_AND_CITATION_MAP.md)
- [Research synthesis for Art Optimizer](06_ART_OPTIMIZER_RESEARCH_SYNTHESIS.md)
- [Core mechanics and user-actions design review](07_CORE_MECHANICS_AND_USER_ACTIONS_DESIGN_REVIEW.md)
- [Experiment and evaluation plan](08_EXPERIMENT_AND_EVALUATION_PLAN.md)
- [From image anchors to composable concept lanes](09_ATTRIBUTE_LIBRARY_AND_ANCHORING_EXPLORATION.md)
- [Concept-lanes executable UI experiment specification](10_CONCEPT_LANES_UI_EXPERIMENTS.md)
- [Round 1 root-cause review](11_ROUND_1_ROOT_CAUSE_REVIEW.md)
- [Round 1 observation-to-code matrix](11A_ROUND_1_OBSERVATION_TO_CODE_MATRIX.md)
- [Five mathematical partial solutions](12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md)
- [Ten ideals and divergent product designs](13_TEN_IDEALS_AND_DIVERGENT_PRODUCT_DESIGNS.md)
- [Round 1 source feedback note](source_notes/ROUND_1_FEEDBACK_NOTE_2026-08-22.md)
- [Canonical citation ledger](CITATION_LEDGER.md)

## Round 1 finding

The first real FLUX.2 Klein session showed that the implementation is a stable controlled-search baseline, but the visible product language implies stronger capabilities than the renderer and concept model provide.

The central mismatch is:

```text
implemented
    preference search over eight hand-authored prompt-embedding coordinates

implied
    parent-conditioned image evolution plus reusable visual-concept learning
```

The [Round 1 root-cause review](11_ROUND_1_ROOT_CAUSE_REVIEW.md) separates this into command semantics, stochastic policy, perceptual slate diversity, renderer ancestry, concept evidence, and experiment-policy boundaries. The tracking umbrella is [issue #10](https://github.com/nbardy/art-optimizer/issues/10).

## Source policy

The reviews prefer, in this order:

1. peer-reviewed papers and official proceedings;
2. an author's thesis or project page;
3. official source repositories;
4. arXiv manuscripts when no archival version exists;
5. author essays for ideas that were published as essays rather than papers.

The source type matters. Ryan Murdock's *Generative Recommenders* is an unusually relevant research essay and prototype, but it is not presented here as a peer-reviewed evaluation. Evan Shimizu's *Design Adjectives* is a peer-reviewed UIST paper backed by a doctoral thesis, released code, user studies, and professional case studies. Recent systems such as MultiBO and GimmBO are cited as preprints unless and until an archival publication is identified.

## Claim labels

The documents use the following labels where useful:

- **Established by source:** directly supported by a cited paper, thesis, or released implementation.
- **Interpretation:** our reading of the source and its implications.
- **Art Optimizer decision:** a deliberate product or architecture choice.
- **Hypothesis:** an empirical claim that still needs testing.
- **Non-claim:** language the project should explicitly avoid.

## High-level conclusion

The reviewed literature supports a strong decomposition:

```text
persistent preference representation
        +
fast branch-local preference learning
        +
uncertainty-aware candidate selection
        +
a compact, versioned generator control space
        +
an interaction model that preserves agency and recoverability
```

The Round 1 postmortem adds several distinctions that must not be collapsed again:

```text
comparison anchor
    != proposal center
    != generative parent
    != stochastic root
    != visual concept
    != persistent taste mode
    != UI experiment policy
```

No single reviewed system supplies that entire stack. Art Optimizer's contribution is therefore best described as a specific integration and experimental platform, not as proof that every component is already optimal.
