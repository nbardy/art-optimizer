# Experiments

This directory converts research ideas into falsifiable, reproducible treatments. Reviews explain why an experiment may matter; experiment folders state exactly what runs and what evidence would promote it.

## Required files

Every experiment topic should contain:

```text
README.md
    hypothesis
    baseline
    treatments
    controlled and varying factors
    instrumentation
    metrics
    failure criteria
    promotion gate
    non-claims

RESULTS_TEMPLATE.md or results/<receipt>.md
    commit and environment
    model/configuration
    raw counts and metrics
    human annotations
    failures
    conclusion
```

Add scripts/configs only when they are executable. Do not create placeholder abstraction files.

## Experiment rules

1. Preserve the current baseline and name it explicitly.
2. Change one coherent policy bundle or use a factorial design that identifies interactions.
3. Record seed/noise relation, action, renderer mode, model/basis revisions, and policy ID for every generated candidate.
4. Measure candidate diversity on outputs, not only control coordinates.
5. Keep neutral novelty requests separate from preference observations.
6. A concept-learning experiment must use repeated visual evidence; one accepted action delta is provisional evidence only.
7. A parent-evolution claim requires a renderer that actually consumes parent state.
8. UI treatments that share the same policy are presentation studies, not algorithm comparisons.
9. Report negative and broken results.
10. Never commit model checkpoints or large generated corpora.

## Current rounds

- [`round2/`](round2/README.md): repair semantics, validate representations, test random soft directions, compare controlled search with true evolution, and build provisional visual concepts.

## Receipt naming

Use:

```text
results/YYYY-MM-DD_<policy-id>_<short-purpose>.md
```

Large artifacts should be stored outside Git and referenced by digest and location.
