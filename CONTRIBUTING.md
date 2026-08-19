# Contributing to Art Optimizer

Art Optimizer is currently a research-and-design-stage open-source project. Contributions are welcome, especially when they make an assumption executable, measurable, or easier for users to understand.

## Useful contribution types

- interface prototypes for the single-canvas/four-corner interaction;
- renderer adapters for open image models;
- deterministic seed and initial-noise replay tests;
- preferential-learning and slate-selection implementations;
- simulated-user benchmarks for optimizer behavior;
- accessibility and touch-interaction improvements;
- research notes that distinguish demonstrated results from hypotheses;
- safety, provenance, licensing, and dataset documentation.

## Design rules

Changes should preserve the core distinctions in the documentation:

- preview versus commit;
- navigation choice versus durable favorite;
- reroll versus new-world reset;
- integer seed versus materialized noise state;
- rendered asset versus authoritative generative state;
- long-term taste prior versus branch-local preference;
- model-independent product contracts versus model-specific interventions.

A proposal that intentionally changes one of these distinctions should explain why and update the relevant architecture decision and tests.

## Pull requests

A focused pull request should include:

1. the user or research problem;
2. the changed behavior or contract;
3. evidence, benchmarks, or a test plan;
4. compatibility and migration impact;
5. model, dataset, and dependency license implications;
6. screenshots or a short recording for interface changes.

Do not present vendor benchmark claims as independent measurements. Record hardware, precision, resolution, batch size, inference steps, software revisions, and warm/cold state for performance results.

## Development direction

The intended initial stack is a TypeScript web client plus a Python control plane, optimizer, and renderer. Exact dependency choices remain open until the first executable vertical slice lands. See:

- [UI design](docs/UI_DESIGN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Code design](docs/CODE_DESIGN.md)
- [Research notes](docs/RESEARCH_NOTES.md)

## Conduct

Be direct about uncertainty, kind in review, and generous with attribution. Creative-preference systems can easily overstate what they infer about a person; describe observed interaction evidence rather than claiming to know a user’s identity or essential taste.
