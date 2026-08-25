# Track CQ-2 — Types, Control Flow, Fallbacks, and Dependency Surface

## Executive finding

The code uses Pydantic and dataclasses extensively, but the important boundaries are still **stringly typed and dictionary shaped**. Most branching is not caused by inherently complex product logic; it is caused by passing partially validated dictionaries across treatment, storage, and UI boundaries and then repairing uncertainty with `if`, fallback values, and broad exceptions.

The dependency list is modest, but reproducibility is weaker than the package count suggests because model and numerical dependencies are broadly ranged and real model revisions are optional.

## 1. Good type foundations

Useful foundations already exist:

- Pydantic models in [`domain.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/domain.py);
- frozen renderer/model dataclasses in [`model_codec.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/model_codec.py);
- renderer `Protocol` in [`rendering.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/rendering.py);
- narrow planner and choice-model classes;
- explicit action dimensions and finite-value validation.

These are worth preserving.

## 2. The most important data is still raw dictionaries

### Event store

[`event_store.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/event_store.py) persists:

```python
kind: str
payload: dict[str, Any]
```

Every consumer must know the correct payload shape through convention. There is no central event union, schema revision, or payload digest.

### Public snapshots

[`service._public_snapshot`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py) returns a large `dict[str, Any]`. `EmergentTasteExperiment` then copies and augments that dictionary. `TasteGalleryService` reads fields by string path.

A breaking field change is discovered at runtime, often after a base mutation has already committed.

### Gallery construction

[`taste_gallery.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/taste_gallery.py) builds intermediate cells as:

```python
specs: list[dict[str, object]]
```

and repeatedly casts values back out. A `GalleryCellSpec` dataclass would remove most casting and impossible states.

## 3. Replace enum-plus-optionals with discriminated unions

`NewWorldPayload` in [`domain.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/domain.py) contains:

```python
mode: Literal["taste_guided", "neutral", "composition"]
target_action: list[float] | None
```

and a validator enforces which combinations are legal. The service then branches again and revalidates.

Prefer:

```python
class TasteGuidedWorld(CommandBase):
    kind: Literal["taste_guided"]

class NeutralWorld(CommandBase):
    kind: Literal["neutral"]

class CompositionWorld(CommandBase):
    kind: Literal["composition"]
    target_action: ActionVector

CreateWorld = Annotated[
    TasteGuidedWorld | NeutralWorld | CompositionWorld,
    Field(discriminator="kind"),
]
```

Then the reducer branches once on the type and each branch has all required data.

The same pattern should cover:

- `ChooseCandidate` versus `RejectSlate` versus `RequestNewDirections`;
- gallery generate versus gallery activate;
- candidate render state;
- typed persistent events;
- treatment-specific preference effects.

## 4. Fallback inventory

Some fallbacks are appropriate at I/O boundaries. Several currently hide semantic corruption.

### High-risk silent fallbacks

1. **Missing prequential receipt becomes uniform probability.**  
   [`EmergentTasteEngine.fit_state`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py) uses `1 / choice_count` when a receipt is absent. A malformed or incompatible event silently changes model-selection evidence.

2. **Chosen candidate is automatically added to exposure.**  
   [`BayesianChoiceModel.update_choice`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/preference.py) repairs an inconsistent command instead of rejecting it. This weakens exposure auditability.

3. **Non-finite planner scores fall back to the first available candidate.**  
   [`CandidatePlanner._argmax_available`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/planner.py) converts numerical failure into a plausible slate.

4. **Gallery strength parsing drops invalid tokens.**  
   [`static/taste_gallery.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/taste_gallery.js) filters non-finite values instead of reporting invalid configuration.

5. **Session resume failures erase local session identity.**  
   Both `app.js` and `emergent_tastes.js` catch any error and delete the stored session. A temporary network error is treated like a nonexistent session.

6. **Local storage read/write failures are swallowed.**  
   This is reasonable for optional UI convenience, but the comment calls the interaction “image evolution,” reinforcing obsolete product semantics.

### Compatibility fallbacks that should expire

`CommandPayload.expected_version` remains as a compatibility alias for `expected_mutation_version`. This causes every command to resolve two fields forever. Version compatibility should live at one API adapter, not inside the core command type.

## 5. Exception structure

Broad exceptions are concentrated in effect boundaries, which is partly legitimate:

- renderer worker boundary;
- world creation render;
- browser network requests.

The problem is that exception classes do not carry typed failure information. A renderer failure becomes `str(error)`, and UI behavior cannot distinguish:

```text
retryable resource exhaustion
invalid model configuration
content-policy rejection
cancelled obsolete render
corrupt cache
permanent unsupported operation
```

Define a closed renderer-result type:

```python
RenderResult = RenderSucceeded | RenderCancelled | RenderRetryableFailure | RenderPermanentFailure
```

Then the candidate state transition can be straight-line and testable.

## 6. Dependency review

[`pyproject.toml`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/pyproject.toml) has a reasonably small core:

- FastAPI / Uvicorn;
- Pydantic;
- NumPy;
- Pillow;
- SciPy.

The model extra adds Torch, Diffusers, Transformers, Accelerate, Safetensors, Hugging Face Hub, and SentencePiece.

### Strengths

- model dependencies are optional;
- `trust_remote_code=False`;
- package versions are included in render request metadata;
- renderer cache digests include many generation parameters;
- core CPU tests do not require model downloads.

### Risks

1. **No lock or constraints file.** Broad ranges allow numerical behavior and pipeline APIs to drift.
2. **Model revision is optional.** Default “latest compatible checkpoint” is not a reproducible research condition.
3. **Diffusers pipeline APIs are brittle.** The conditioning adapters depend on exact `encode_prompt` return signatures.
4. **Runtime identity is incomplete.** [`config.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/config.py) fingerprints model/source/revision/codec/conditioning but omits image size, dtype, offload mode, device, inference steps, guidance, and embedding strength.
5. **SciPy has several unrelated roles.** It supplies optimization, Sobol sampling, and assignment. This is acceptable, but mathematical components should declare the exact routines and tolerances as model policy rather than importing implementation defaults implicitly.

## 7. Shared contract target

Introduce a small shared contract module:

```python
ActionVector
RepresentationScope
RenderSpec
RenderReceipt
ChoiceSlate
PreferenceObservation
TreatmentConfiguration
CommandEnvelope
CommandResult
```

Each should be immutable and hashable or have a canonical digest. Functions should accept and return those objects, not arbitrary snapshots.

The target is not object-oriented ceremony. A functional pipeline can then be:

```python
scope = resolve_scope(renderer, session)
slate = qualify_exposure(scope, command, round)
observation = record_choice(scope, slate, command.outcome)
projection = taste_engine.fit(observation_log)
```

Each line has a typed input and output. Invalid combinations fail at construction, not several `if` statements later.

## Verdict

**Type usage:** present but weakest at the most consequential boundaries.  
**Fallback burden:** moderate-to-high; several fallbacks convert corrupted evidence or numerical failure into normal-looking state.  
**Dependency burden:** modest, but model/numerical reproducibility needs pinning and fuller scope identity.  
**Priority:** define event/command/scope types and delete silent evidence fallbacks before attempting broad line-count reduction.
