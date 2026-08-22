# Art Optimizer Review Corpus

**Status:** internal research and design review  
**Review date:** 2026-08-22

This directory separates prior work, project interpretation, postmortems, and raw source evidence. It exists to prevent experimental proxies from being promoted into product claims without support.

## Source policy

Prefer, in order:

1. peer-reviewed papers and proceedings;
2. author theses and official project pages;
3. official source repositories;
4. preprints when no archival version exists;
5. author essays for work published primarily as essays.

Source type matters. Ryan Murdock's work is cited as an author essay and released prototypes, not a controlled production evaluation. Evan Shimizu's *Design Adjectives* is peer-reviewed work backed by a thesis, source code, user studies, and professional case studies.

## Foundational research reviews

1. [Ryan Murdock: Generative Recommenders and Preference Priors](01_RYAN_MURDOCK_GENERATIVE_RECOMMENDERS.md)
2. [Evan Shimizu: Design Adjectives](02_EVAN_SHIMIZU_DESIGN_ADJECTIVES.md)
3. [Preference Learning and Preferential Bayesian Optimization](03_PREFERENCE_LEARNING_AND_PREFERENTIAL_BO.md)
4. [Generative Control Spaces and Learned Directions](04_GENERATIVE_CONTROL_SPACES_AND_DIRECTIONS.md)
5. [Interactive Generative Search Systems](05_INTERACTIVE_GENERATIVE_SEARCH_SYSTEMS.md)

Claim-level companions:

- [Murdock claim and citation map](01A_RYAN_MURDOCK_CLAIM_AND_CITATION_MAP.md)
- [Shimizu claim and citation map](02A_EVAN_SHIMIZU_CLAIM_AND_CITATION_MAP.md)
- [Canonical citation ledger](CITATION_LEDGER.md)

## Product synthesis and design

- [Research synthesis for Art Optimizer](06_ART_OPTIMIZER_RESEARCH_SYNTHESIS.md)
- [Core mechanics and user-actions design review](07_CORE_MECHANICS_AND_USER_ACTIONS_DESIGN_REVIEW.md)
- [Experiment and evaluation plan](08_EXPERIMENT_AND_EVALUATION_PLAN.md)
- [From image anchors to composable concept lanes](09_ATTRIBUTE_LIBRARY_AND_ANCHORING_EXPLORATION.md)
- [Concept-lanes UI experiment specification](10_CONCEPT_LANES_UI_EXPERIMENTS.md)

## Round 1 evidence and postmortem

- [Round 1 root-cause review](11_ROUND_1_ROOT_CAUSE_REVIEW.md)
- [Observation-to-code matrix](11A_ROUND_1_OBSERVATION_TO_CODE_MATRIX.md)
- [Five mathematical partial solutions](12_FIVE_MATHEMATICAL_PARTIAL_SOLUTIONS.md)
- [Ten ideals and divergent product designs](13_TEN_IDEALS_AND_DIVERGENT_PRODUCT_DESIGNS.md)

Raw source notes:

- [User Round 1 feedback](source_notes/ROUND_1_FEEDBACK_NOTE_2026-08-22.md)
- [External Round 1 technical review](source_notes/ROUND_1_EXTERNAL_TECHNICAL_REVIEW_2026-08-22.md)

The source notes are preserved separately from project conclusions. Simulation numbers in the external review remain provisional until reproduction code, configuration, and receipts are checked in.

## Round 1 conclusion

The first FLUX.2 Klein session showed that the engineering scaffold is useful, but the representation and product language were misaligned.

```text
implemented
    controlled preference search over eight hand-authored prompt-embedding coordinates

implied
    parent-conditioned image evolution and reusable visual-concept learning
```

The postmortem separates objects that must not be collapsed again:

```text
comparison anchor
    != proposal center
    != generative parent
    != stochastic root
    != preference posterior
    != provisional move
    != visual concept
    != persistent taste mode
    != experiment policy
```

The current implementation remains a valid controlled-search baseline. It is not evidence that the eight axes are perceptually well conditioned, that selected images parent descendants, or that singleton action deltas are visual concepts.

## Claim labels

Use these labels where useful:

- **Established by source:** directly supported by cited work or released implementation.
- **Observed:** directly seen in a recorded session or code path.
- **Interpretation:** our inference from evidence.
- **Project decision:** deliberate product/architecture choice.
- **Hypothesis:** requires an experiment.
- **Non-claim:** language the project should avoid.

## Next step

Research proposals move into [`../experiments/`](../experiments/README.md) only when they have a baseline, treatment, instrumentation plan, failure criteria, and promotion gate. The current Round 2 queue is [`../experiments/round2/README.md`](../experiments/round2/README.md).
