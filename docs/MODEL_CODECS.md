# Model Codecs and Experiment Boundaries

**Status:** implemented v0.3 contract

## One canonical action type

The optimizer emits one bounded eight-dimensional action. It does not know whether the selected renderer is procedural, FLUX.2 Klein, or Krea 2 Turbo.

```text
optimizer action
  -> SemanticDirectionCodec
  -> model conditioning adapter
  -> ImageRenderer
  -> RenderedArtifact
```

All model dispatch is data-driven from the profile registry in `model_codec.py`. The service does not contain model-family branches.

## Local/open-weight policy

The supported real-model profiles load checkpoints locally through Diffusers. There is no hosted generation API path.

- `flux2-klein`: Apache-2.0 weights, `Flux2KleinPipeline`, four steps.
- `krea2-turbo`: local open weights under the Krea 2 Community License, `Krea2Pipeline`, eight steps.

“Open weights” and “OSI open source” are recorded separately. Krea is open-weight and inspectable but its custom community license is not OSI-approved. Deployers must review its revenue threshold and content-filter obligations.

## Embedding directions

Each semantic axis has a negative and positive endpoint phrase. For a fixed world prompt, the codec encodes the base and endpoint prompts once and caches the resulting direction bank:

\[
d_i = \frac{E(p_i^+) - E(p_i^-)}{2}.
\]

Directions are RMS-normalized relative to the base embedding and mixed conservatively:

\[
E(a) = E(p_0) + \frac{\eta}{\sqrt d}\sum_i a_i d_i.
\]

The model-specific surface is intentionally tiny:

- FLUX accepts `prompt_embeds` and reconstructs its text position IDs.
- Krea accepts `prompt_embeds` plus `prompt_embeds_mask`.

Those two signatures are represented by two conditioning adapters. The renderer, cache, optimizer, event model, and UI remain shared.

`ART_OPTIMIZER_CONDITIONING_MODE=prompt` keeps a prompt-compilation baseline for controlled experiments.

## Adding another model

A compatible model needs:

1. one immutable `ModelProfile`;
2. an existing backend (`diffusers` today);
3. an existing conditioning adapter, or one small adapter if its embedding call signature differs;
4. codec and control-basis revisions;
5. license and deployment metadata;
6. fake-pipeline tests;
7. real control-basis, replay, memory, and latency receipts.

It should not add model checks to the service or frontend.

## Algorithm experiments

The local learner, acquisition planner, persistent atlas, renderer, and UI transport are separate modules. Raw interaction events are durable facts; projections can be rebuilt under another learner.

A new algorithm should implement the same operations used by the service:

```text
restore snapshot
predict utility and uncertainty
sample a utility function
update from one slate choice
produce a versioned snapshot
```

A new acquisition policy consumes the same anchor, posterior, trust state, compatible atlas coordinates, and RNG, and returns four typed proposals. Algorithm selection should happen in the process composition root—not as conditionals inside request handlers.

## UI experiments

The current browser is one client of the HTTP/SSE contract. A grid, scrolling feed, pairwise chooser, native mobile app, or research dashboard can use the same API without importing model or optimizer code.

UI experiments must preserve event semantics: preview is not commitment, reroll selects the anchor, exposure is explicit, favorite is durable taste evidence, and New world is not a negative label.

## Node deployment

For private research, prefer an SSH tunnel or VPN. Directly exposing the development server requires a firewall/security-group rule, but it currently provides neither authentication nor TLS. Put an authenticated HTTPS reverse proxy in front of it before broader access.
