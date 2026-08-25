# Deep Review Packet — 2026-08-24

**Repository:** `nbardy/art-optimizer`  
**Audited revision:** [`893e4049105ac56a829edadface3a35a61d087d5`](https://github.com/nbardy/art-optimizer/commit/893e4049105ac56a829edadface3a35a61d087d5)  
**Method:** independent review tracks, reconciled only in the final synthesis  
**Status:** review notes; no production behavior changed

## Why this packet exists

This review asks five separate questions that should not be collapsed into one general feeling about the code:

1. **Code quality** — how much prototype slop and duplication exists; where typed data and shared functional machinery can replace branches, fallbacks, and copied controllers.
2. **Design completeness** — whether the current runtime is actually a model of the product and research goal that was discussed.
3. **Bugs** — concrete correctness, concurrency, persistence, replay, renderer, and UX failures.
4. **Mathematical model** — whether the problem has been stated cleanly enough that a mathematician could return well-defined objects and algorithms.
5. **Mathematical correctness** — whether the implemented likelihoods, gradients, inference, model selection, and geometry match their claims.

The raw notes intentionally retain overlapping observations. Agreement across independently framed passes is useful evidence; disagreements are resolved in [`final_synthesis.md`](final_synthesis.md).

## Review tracks

### Code quality

- [`code_quality/01_architecture_and_line_count.md`](code_quality/01_architecture_and_line_count.md)
- [`code_quality/02_types_control_flow_and_dependencies.md`](code_quality/02_types_control_flow_and_dependencies.md)
- [`code_quality/03_frontend_shared_modules.md`](code_quality/03_frontend_shared_modules.md)

### Design completeness

- [`design_completeness/01_goal_to_runtime_matrix.md`](design_completeness/01_goal_to_runtime_matrix.md)
- [`design_completeness/02_experiment_and_state_model.md`](design_completeness/02_experiment_and_state_model.md)

### Bugs

- [`bugs/01_persistence_concurrency.md`](bugs/01_persistence_concurrency.md)
- [`bugs/02_gallery_renderer_frontend.md`](bugs/02_gallery_renderer_frontend.md)

### Mathematical model

- [`mathematical_model/01_formal_problem_landscape.md`](mathematical_model/01_formal_problem_landscape.md)
- [`mathematical_model/02_model_family_and_api.md`](mathematical_model/02_model_family_and_api.md)

### Mathematical correctness

- [`mathematical_correctness/01_ideal_point_and_hmm.md`](mathematical_correctness/01_ideal_point_and_hmm.md)
- [`mathematical_correctness/02_legacy_learner_and_embedding_geometry.md`](mathematical_correctness/02_legacy_learner_and_embedding_geometry.md)

## Reconciled outputs

- [`final_synthesis.md`](final_synthesis.md)
- [`recommended_followup.md`](recommended_followup.md)

## Reading order

For a fast decision read:

1. `final_synthesis.md`
2. `bugs/01_persistence_concurrency.md`
3. `mathematical_correctness/01_ideal_point_and_hmm.md`
4. `recommended_followup.md`

For an implementation refactor, read the three code-quality notes first. For a research handoff, read the two mathematical-model notes first.
