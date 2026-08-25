# Track DC-2 — Experiment, State, and Provenance Completeness

## Executive finding

The repository has many provenance fields, but it does not yet have a single explicit experiment-state model. A session is primarily a mutable T0 search session; treatments layer additional interpretation on top. That makes it possible to run the UI, but difficult to answer basic scientific questions such as:

- Which exact policy generated this slate?
- Which preference engine was authoritative?
- Which model configuration produced this observation?
- Did the atlas influence this session?
- Is this gallery based on the same taste revision now displayed?
- Can the result be reconstructed from facts alone?

The state model is operationally useful, but scientifically incomplete.

## 1. Session state is T0 state with treatment projections attached

[`SessionState`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/domain.py) owns:

- one active world;
- designs and branch nodes;
- one legacy Gaussian posterior;
- one legacy search state;
- one active candidate round;
- favorites and history.

There is no field for:

```text
treatment ID
treatment configuration
representation scope digest
authoritative preference-engine ID
shadow projection IDs
observation schema revision
planner policy revision per branch
taste-family revision
```

`EmergentTasteExperiment` adds a response-only `treatment` dictionary and rebuilds its state from separate events. This is not the same as the session being assigned to a treatment.

## 2. Branch checkpoints preserve only the legacy learner

`BranchNode` contains:

```python
design_id
parent_branch_node_id
posterior: GaussianSnapshot
search_state: SearchState
```

It does not point to an emergent-taste revision or an atlas revision. Restoring a branch restores the historical legacy learner but keeps the newest emergent event stream. The UI says “Resume from exemplar,” but the operation combines:

```text
historical image + historical legacy posterior
with current global emergent-taste projection
```

That can be a valid product operation, but it is not a historical restoration of the complete treatment state.

The product needs two distinct commands:

- **Revisit image using current taste state**;
- **Fork from historical experiment checkpoint**.

## 3. Non-navigation preference updates are not checkpointed

The base `reroll`/anchor-win path updates `state.active_posterior` and search radius but does not create a new `BranchNode`. A later history restore loads the older posterior from the branch and discards those updates.

This is both a bug and a state-model incompleteness: the system treats branch identity as image navigation identity, while preference state can change without image navigation.

A correct state model needs immutable checkpoints for every preference-bearing command, even when the design ID stays unchanged.

## 4. Event log is not a complete event source

The code calls the SQLite table `events`, and many events are useful audit facts. But state is not reconstructable solely from them:

- candidate render progress uses `save_session` directly in places;
- some event payloads omit full prior state or model policy;
- command results are stored separately;
- atlas projection is stored separately;
- emergent projection is reconstructed only from its own events;
- browser concepts never reach the server;
- events have no universal schema revision.

The honest term is **audit/event log plus authoritative projections**, not an event-sourced system.

## 5. Representation scope is incomplete

The emergent fixed-root scope hashes:

```text
seed
prompt
renderer_revision
control_basis_revision
```

The gallery scope adds model ID, codec revision, conditioning mode, and action dimension. Neither consistently includes:

- resolved model source and checkpoint revision;
- image size;
- dtype and offload mode;
- inference steps and guidance;
- embedding strength;
- Diffusers/Torch versions;
- exact direction-bank instance digest.

[`Settings.from_env`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/config.py) also omits several of these from the runtime database directory fingerprint. Old sessions can therefore be loaded under a materially different runtime with the same nominal renderer revision.

## 6. Gallery provenance freezes a center but not a taste revision

`TasteGalleryManifest` records a taste ID, label, center, and center digest. It does not record:

- the exact selected model `K`;
- the fit/policy revision beyond current engine defaults;
- evidence event IDs;
- component assignment lineage;
- posterior uncertainty;
- a stable component revision ID.

Because taste labels can change on refit, `taste-1` is not a durable identity. The center digest preserves what was rendered, which is good, but not why that center was considered a taste.

## 7. Documentation/runtime mismatches

[`docs/TASTE_GALLERIES.md`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/docs/TASTE_GALLERIES.md) says each gallery stores “configuration digests” and that a continued session “inherits the experiment configuration.” The current runtime has no experiment configuration type or digest, and a gallery-created session simply initializes the default emergent engine.

[`docs/EMERGENT_TASTES.md`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/docs/EMERGENT_TASTES.md) describes immutable before-outcome events, but the event is appended only after the base command succeeds. A crash can lose it.

Documentation should be generated from or tested against runtime contracts where possible.

## 8. Recommended state model

### Session assignment

```python
TreatmentAssignment(
    treatment_id,
    treatment_revision,
    configuration,
    configuration_digest,
    authoritative_engine,
    shadow_engines,
    representation_scope,
)
```

### Immutable checkpoint

```python
ExperimentCheckpoint(
    checkpoint_id,
    design_id,
    branch_parent,
    search_projection_revision,
    taste_projection_revision,
    atlas_policy_revision,
    created_by_event_id,
)
```

### Typed facts

```python
PreferenceChoiceRecorded
NewDirectionsRequested
GalleryGenerated
GalleryCellActivated
CheckpointRevisited
CheckpointForked
RenderFailed
```

### Projection rule

All visible state should be reproducible from:

```text
initial assignment + immutable facts + declared reducer revisions
```

Operational caches may remain, but a replay mismatch should be test failure.

## Verdict

**Operational state completeness:** adequate for a local prototype.  
**Experiment-state completeness:** weak.  
**Replay claim:** partial audit replay, not full event sourcing.  
**Highest priority:** introduce treatment assignment, exact representation scope, and preference-state checkpoints before adding an authoritative taste planner.
