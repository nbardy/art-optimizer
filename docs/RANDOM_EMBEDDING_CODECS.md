# Random Embedding Point Codecs

**Status:** implemented experimental treatment  
**Route:** `/ui/direction-lab`  
**Treatment ID:** `random-direction-lab`

## Why this exists

The first real-model test found that moving through eight authored prompt contrasts produced changes that were often too small and too predictable. Subsequent work improved preference inference and state correctness but left that generator-facing representation untouched.

Direction Lab changes the upstream experiment directly:

```text
same prompt
same diffusion seed
same model and inference settings
four direct prompt-embedding points
no authored color / composition / realism strings
```

It is deliberately separate from the taste learner. The first question is whether direct non-string movement in the conditioning representation produces useful visual variation.

## Geometry

Let the encoded base prompt be

\[
e_0\in\mathbb R^D.
\]

For one slate, codec \(c\) and point seed \(q\) deterministically produce four unit-RMS perturbations

\[
b^{(c,q)}_1,\ldots,b^{(c,q)}_4,
\qquad
\operatorname{RMS}(b_j)=1.
\]

At shell radius \(r>0\), the candidate conditioning points are

\[
\boxed{e_j=e_0+\operatorname{RMS}(e_0)\left(x+r b_j\right)}
\]

where \(x\) is the accumulated offset of previously selected points. The initial center has \(x=0\).

Therefore every first-round candidate is exactly

\[
\operatorname{RMS}(e_j-e_0)=r\operatorname{RMS}(e_0),
\]

not a draw that may land near zero. There is no center candidate and no radial Gaussian distribution to tune indirectly.

Selecting candidate \(j\) appends a replayable path step

\[
x\leftarrow x+r b_j.
\]

The next slate samples a new set of shell directions around that selected embedding center while retaining the same diffusion seed.

## Why a shell rather than an unconstrained Gaussian

For \(z\sim\mathcal N(0,I_D)\),

\[
\|z\|_2^2\sim\chi^2_D,
\]

so in high dimension its norm concentrates near \(\sqrt D\), not near zero. A raw Gaussian already has shell-like norm concentration, but its realized radius is only implicit and varies with representation size. Direction Lab normalizes every draw to exact unit RMS so:

- candidate strength has a direct, model-independent meaning;
- the center is never sampled accidentally;
- codecs can be compared at matched conditioning displacement;
- pairwise spacing is known before rendering;
- a radius slider changes the actual embedding displacement, not an indirect authored-action scale.

This does **not** imply that arbitrary Gaussian embedding points remain on the learned text manifold. They may be inert, destructive, or collapse toward common image-model modes. That empirical failure is exactly what the four codecs compare.

## Four selectable codecs

### 1. Gaussian shell

Draw four independent full-tensor Gaussian vectors, remove the constant mode, and normalize each to unit RMS:

\[
g_j\sim\mathcal N(0,I_D),
\qquad
b_j=\frac{g_j-\bar g_j\mathbf1}{\operatorname{RMS}(g_j-\bar g_j\mathbf1)}.
\]

In very high dimension these directions are approximately orthogonal without forcing it. This is the simplest direct test of random embedding points.

### 2. Orthogonal shell

Draw a \(D\times4\) Gaussian matrix and take a reduced QR factorization:

\[
G=QR.
\]

The four columns of \(Q\), reshaped to the embedding tensor and RMS-normalized, are exactly orthogonal. At matched radius, each pair has ideal separation

\[
\operatorname{RMS}(r b_i-r b_j)=r\sqrt2.
\]

This is the cleanest maximal-separation baseline.

### 3. Low-rank shell

For a token-by-channel representation, generate

\[
B_j=U_jV_j,
\qquad
U_j\in\mathbb R^{T\times k},
\quad
V_j\in\mathbb R^{k\times C},
\quad k\le4,
\]

then normalize to unit RMS. The token factors are centered so the perturbation has zero global mean while retaining rank at most four.

This tests whether structured, smoother perturbations are more useful than independent elementwise noise while still avoiding natural-language axes.

### 4. Antipodal cross

Generate two orthogonal random directions \(u,v\) and display

\[
+u,\;-u,\;+v,\;-v.
\]

This is not optimized for four unrelated outcomes. It asks a sharper question: does either random line have a coherent signed effect? A useful line should often produce interpretable opposition between its positive and negative ends.

## Variance receipts

The API returns geometry known before any image is rendered:

- candidate RMS offset from the original prompt embedding;
- center RMS offset;
- all six pairwise candidate RMS distances;
- minimum and maximum pairwise spacing;
- the direction cosine matrix;
- effective rank of the four directions;
- confirmation that all candidates share one diffusion seed;
- confirmation that authored string axes were not used.

For direction matrix \(B\in\mathbb R^{4\times D}\), the reported effective rank is the participation ratio

\[
r_{\mathrm{eff}}
=
\frac{\left(\sum_i\sigma_i^2\right)^2}
{\sum_i\sigma_i^4},
\]

where \(\sigma_i\) are the singular values of \(B\).

These receipts distinguish requested conditioning variance from the rendered model response. The latter still depends on the local fixed-seed generator map

\[
I=G_s(e),
\qquad
\delta I\approx J_s(e)\delta e.
\]

Direction Lab controls \(\delta e\) exactly; the visual test estimates how the unknown Jacobian \(J_s\) responds.

## Radius interpretation

The radius is measured directly relative to base-embedding RMS:

```text
r = 0.10   candidate perturbation RMS is 10% of base prompt RMS
r = 0.40   candidate perturbation RMS is 40% of base prompt RMS
r = 1.00   candidate perturbation RMS equals base prompt RMS
```

The default is intentionally much larger than the original authored-axis local movement. Large values may leave the useful conditioning region; that is visible and reversible through the radius control and center-history buttons.

## Reproducibility

A slate is determined by:

- model and resolved runtime revisions;
- base prompt;
- diffusion image seed;
- codec ID and codec revision;
- random point seed;
- radius;
- full selected-center path.

The render manifest stores the candidate offset digest and all of those parameters. Repeating the same request reuses the exact cached images.

## Explicit non-claims

This first implementation does not claim that:

- random points are semantic;
- the four codecs are equally on-manifold;
- a useful point transfers to another prompt or model;
- visual similarity can be predicted from embedding RMS alone;
- selecting a point trains the emergent-taste model;
- this is parent-conditioned image evolution.

It provides the missing upstream ablation: direct, deliberately noncentral, non-string embedding search at a controlled fixed seed.
