# Round 1 Observation-to-Code Matrix

**Date:** 2026-08-22  
**Issue:** [#10](https://github.com/nbardy/art-optimizer/issues/10)  
**Source note:** [Round 1 feedback](source_notes/ROUND_1_FEEDBACK_NOTE_2026-08-22.md)

This matrix keeps the postmortem auditable. “Observed” means directly experienced in the first FLUX session or directly inspectable in code. “Inference” means a plausible causal explanation that still requires a controlled experiment.

| Observation | Code evidence | Status | Round 2 instrumentation |
|---|---|---|---|
| Reroll can train negative preference | `ArtOptimizerService.reroll`: anchor winner, weight `0.35` after two exposed candidates | Observed in code | log `command_semantics`, qualified alternatives, update weight, before/after posterior |
| Reroll can oppose browser concepts | `ConceptLibrary.observeReroll` | Observed in code | persist concept observation facts separately from derived concept state |
| Fewer than two exposed candidates produces no preference update | `ArtOptimizerService.reroll`: `round_skipped` branch | Observed in code | distinguish loading failure, user shuffle, and intentional none-of-these |
| Four candidates look too similar | Round 1 test | Observed in session | image embeddings, pairwise perceptual distances, duplicate rate, seed relation |
| Planner is numerically diverse | `CandidatePlanner._build_pool` and role scores | Observed in code | persist hidden-pool statistics and selected action distances |
| Planner does not measure rendered diversity | `CandidatePlanner` consumes actions/posterior only | Observed in code | render/estimate a feature pool before final slate selection |
| All candidates in a world use the world seed | `ArtOptimizerService._render_candidate` passes `world.seed` | Observed in code | candidate-level `noise_policy`, `seed`, and parent noise provenance |
| Embedding perturbations are conservative | FLUX profile: strength `0.24`, four steps, guidance `1.0`, coherence finish | Observed in code | benchmark strength and prompt/basis variants with fixed-seed sweeps |
| Clicking does not edit current pixels | commit promotes existing candidate; renderer takes prompt, seed, action | Observed in code | renderer mode and parent-conditioning provenance |
| Eight axes are hand-authored | `_AXES` in `model_codec.py` | Observed in code | effect size, monotonicity, entanglement, validity radius per axis/prompt/model |
| A selected movement often creates a lane | `observeCommit`: merge threshold `0.82`, else immediate concept | Observed in code | provisional assignment probability, support count, visual-delta similarity |
| Singleton lane can become active | support starts at `1`; AUTO threshold `0.25` | Observed in code | explicit concept lifecycle state and promotion audit |
| Concept model ignores image content | browser concept record stores direction/magnitude/exemplar only | Observed in code | action delta + visual delta + caption delta + context + seed relation |
| Concept state is browser-local | localStorage key `artOptimizerConceptLibrary/v1` | Observed in code | server-side evidence ledger and versioned projections |
| UI routes share one hypothesis | same API/session/planner/learner/concept controller | Observed in code | policy ID and independent projection state per experiment |
| Lane labels may bias choices | labels are rendered by concept/lane UIs | Inference | blinded label/no-label treatment |
| Same-seed control improves attribution but hurts novelty | fixed world seed plus prompt-embedding changes | Inference supported by session | hybrid factorial seed/control slate |
| Action-space distance poorly predicts perceptual distance | near-duplicates despite broad action proposals | Observed outcome; causal model incomplete | learn local action-to-image Jacobian and compare metrics |

## Minimum event-schema additions

```text
CandidateGenerated
    experiment_policy_id
    renderer_mode
    seed
    seed_relation_to_anchor
    parent_design_id
    parent_conditioning_id
    action
    visual_embedding_id
    hidden_pool_source
    selection_role

UserCommand
    command_kind
    semantic_label
    preference_effect
    qualified_candidate_ids

ConceptObservation
    action_delta
    visual_delta_embedding
    context_id
    seed_relation
    outcome
    assignment probabilities
    lifecycle result
```

The matrix should be updated after each controlled experiment. It is not a substitute for metrics or user studies; it is a guard against forgetting which conclusions came from code, which came from the first session, and which remain hypotheses.
