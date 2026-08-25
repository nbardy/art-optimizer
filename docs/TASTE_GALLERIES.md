# Seed-by-Strength Taste Galleries

## Geometry

For taste center \(\theta_k\), strength \(s\), and row seed \(r\):

\[
a(s,k)=\operatorname{clip}(s\theta_k,-1,1),
\qquad I_{r,s}=G(r,p,a(s,k)).
\]

Rows vary deterministic seeds. Columns vary only scalar strength. The first row uses the current world seed; other seeds are derived from the immutable gallery identity and shuffle nonce.

## Evidence boundary

Generating, opening, previewing, or reshuffling a gallery creates no preference observation. A gallery changes seed and therefore is not a qualified fixed-root comparison slate.

Continuing from a cell creates a fresh fixed-root session at that exact seed and action with an empty latent-mode history.

## Execution

Gallery identity and cell render identities are deterministic. Rendering uses a bounded semaphore rather than launching the full grid without limit. Concurrent requests for one source session are serialized. If any cell fails, newly created successful cells from that request are cleaned up and the API returns an explicit operation error; pre-existing cache artifacts are preserved.

## Manifest

The immutable gallery event records:

- source session and taste;
- frozen center and digest;
- model/renderer/codec/conditioning/basis scope;
- row seeds and strengths;
- each cell action, clipping state, artifact, and digest;
- explicit `preference_effect = none`.
