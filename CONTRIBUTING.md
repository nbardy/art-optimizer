# Contributing to Art Optimizer

Art Optimizer is a local research application for fixed-root generative search and preference experiments. Contributions should make the current experiment smaller, more correct, more measurable, or easier to understand.

## Before changing behavior

Preserve these distinctions unless the change explicitly defines a new treatment:

- preview is not commit;
- navigation is not durable preference;
- `New directions` is neutral exploration;
- `None fit` is weak anchor preference;
- gallery inspection is not preference evidence;
- fixed-root search is not parent-conditioned image evolution;
- action-preference modes are not automatically semantic visual attributes.

## Development gate

Use Python 3.11 or newer and Node 22 or newer.

```bash
pip install -e '.[dev]'
make check
```

For live verification:

```bash
make dev
make smoke
```

The repository intentionally does not use hosted GitHub Actions. Include the local verification result in the pull-request description.

## Pull requests

Keep changes narrow. A useful pull request states:

1. the user or research problem;
2. the exact behavior or contract changed;
3. tests or failure injection covering it;
4. compatibility and migration impact;
5. model, dataset, and dependency-license implications;
6. explicit non-claims.

Do not combine renderer, learner, planner, and UI changes into one experiment unless the treatment definition requires that bundle.

## Research evidence

Record enough provenance to reproduce a claim:

- model and resolved revision;
- renderer, codec, conditioning mode, and control-basis revision;
- prompt and seed;
- action or strength values;
- hardware, dtype, resolution, and inference steps;
- cold/warm state and latency;
- failure cases.

Describe observed interaction evidence rather than claiming an essential or permanent user taste.
