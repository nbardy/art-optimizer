# Seed-by-Strength Taste Galleries

## Interaction

Clicking an exposed taste opens a grid:

```text
rows      deterministic seeds
columns   scalar taste strengths
```

The first row uses the current fixed-root seed. Additional row seeds are derived
deterministically from the immutable gallery ID and a user-controlled seed nonce.
`Shuffle seed rows` increments that nonce.

## Strength definition

For learned taste center `theta_k` and column strength `s`:

```text
a(s,k) = clip(s * theta_k, -1, 1)
```

The neutral action origin is therefore `s=0`, the fitted taste center is `s=1`, and
larger values extrapolate until a coordinate reaches the renderer action bound.
Cells disclose when clipping occurred.

## Immutable manifest

Each gallery event stores:

- source session and taste;
- taste center and digest;
- representation-scope and configuration digests;
- row seeds and strength columns;
- every action vector;
- rendered artifact identity and digest;
- gallery and cell IDs;
- explicit `preference_effect = none`.

Repeated requests with the same gallery specification reuse deterministic renderer
cache identities.

## Evidence boundary

Gallery rendering, previewing, selecting, and seed shuffling never append
`emergent_taste_choice_recorded` events. A grid deliberately changes seed and is not
a qualified fixed-root choice slate.

## Continuing from a cell

`Continue as new fixed-root session` creates a fresh session whose root is the
selected cell's exact seed, action, and rendered artifact. The new session inherits
the experiment configuration but starts with zero taste observations.

This preserves provenance while preventing cross-seed browsing from being mistaken
for evidence inside the original fixed-root taste projection.
