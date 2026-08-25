# Track CQ-1 — Architecture, Slop, and Line-Count Reduction

## Executive finding

The repository is not random spaghetti. It has several genuinely useful seams — renderer protocol, codec registry, planner class, Pydantic domain objects, SQLite store — but the application layer has accumulated **substantial prototype orchestration slop**.

The highest-leverage problem is not individual ugly functions. It is that four different concerns are repeatedly fused:

```text
validate a command
mutate session state
persist facts/projections
run side effects and publish UI state
```

That fusion makes every new treatment copy a command wrapper around a large mutable service.

A credible refactor can reduce the **session/treatment orchestration code by roughly 2–3×** and the **browser controller code by roughly 2×**. A whole-repository 5× reduction is not credible without deleting the legacy atlas/concept treatments and much historical support code. Fivefold reduction by abstraction alone would produce worse code.

## 1. The central god object

[`art_optimizer/service.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py) owns all of the following:

- session creation and loading;
- commit, reroll, favorite, world reset, and restore commands;
- branch and world construction;
- choice-model updates;
- atlas evidence;
- renderer task scheduling and cancellation;
- candidate-round creation;
- persistence calls;
- SSE subscription and publication;
- state repair after restart;
- public response projection;
- artifact cleanup for stale renders.

The class is therefore not merely a domain service. It is simultaneously:

```text
command router
mutable aggregate
transaction script
render coordinator
projection builder
SSE hub
repository adapter
recovery daemon
```

That is the main source of conditionals and defensive checks.

### Repeated command skeleton

The public commands repeat a nearly identical protocol:

```python
runtime = await self._get_runtime(session_id)
async with runtime.command_lock:
    cached = self._cached_command(...)
    if cached is not None:
        return cached

    async with runtime.lock:
        self._validate_expected_mutation(...)
        # locate and validate state
        # mutate several fields
        self.store.record_session_event(...)

    # cancel/publish/side effect/start next round
    result = await self._snapshot(runtime)
    self.store.save_command_result(...)
    return result
```

See `commit_candidate`, `reroll`, `favorite`, `new_world`, and `restore` in [`service.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py).

The variation belongs in a typed reducer; the common protocol belongs in one executor.

## 2. Treatment wrappers compound the service rather than compose it

[`art_optimizer/emergent_experiment.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_experiment.py) wraps the base service and reconstructs a second command lifecycle around it. It must:

- lock separately;
- fetch the base snapshot;
- reinterpret exposure;
- create a parallel observation;
- ask shadow models for predictions;
- execute the base command;
- append another event;
- refit a projection;
- augment every response and SSE payload.

[`art_optimizer/taste_gallery.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/taste_gallery.py) goes further and reaches into private service internals:

```python
self.service._design_from_artifact(...)
self.service._sessions[new_session_id] = runtime
await self.service._start_round(runtime)
return await self.service._snapshot(runtime)
```

This is a strong sign that the public domain API is missing. `TasteGalleryService` is effectively a privileged subclass implemented through composition.

## 3. Four preference representations are live

The runtime currently has four different answers to “what has the user learned to like?”

1. branch-local 44-parameter learner in [`preference.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/preference.py);
2. persistent server atlas in [`atlas.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/atlas.py);
3. browser-local `ConceptLibrary` in [`static/experiment_core.js`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/static/experiment_core.js);
4. sticky emergent-taste projection in [`emergent_taste.py`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_taste.py).

The problem is not that multiple experimental models exist. The problem is that three of them still mutate or influence the same session:

- emergent candidate choices update the legacy branch learner;
- candidate commits and branch revisits update the persistent atlas;
- concept UIs maintain browser-local state independently;
- the emergent model observes the same interactions in a parallel event stream.

This multiplies state and makes treatment isolation hard to reason about.

## 4. Recommended architecture

The cleanest target is a small functional core with effectful edges.

### Typed command

```python
Command = (
    ChooseCandidate
    | RejectSlate
    | RequestNewDirections
    | RestoreCheckpoint
    | CreateWorld
    | FavoriteDesign
)
```

### Pure transition

```python
TransitionResult = reduce(session_projection, command, immutable_context)

# result contains:
# - new projection
# - typed facts to append
# - typed jobs to dispatch
# - response intent
```

The reducer should not render, open SQLite, publish SSE, or update a second learner.

### One command executor

```python
async def execute(command):
    current = repository.load_for_update(command.session_id)
    result = reducer.apply(current, command)
    repository.commit(result)
    jobs.submit(result.jobs)
    publisher.publish(result.public_projection)
    return result.public_projection
```

### Treatment policy as data

```python
TreatmentPolicy(
    planner=LegacyPlannerPolicy(...),
    preference=EmergentShadowPolicy(...),
    atlas=DisabledAtlasPolicy(),
    command_semantics=TruthfulCommands(),
    renderer=FixedRootRendererPolicy(),
)
```

A treatment should not require another service wrapper. It should supply policies that the same executor pipes through typed interfaces.

## 5. Realistic line-count reduction

### Backend

Current large orchestration modules:

- `service.py`: roughly a thousand lines;
- `emergent_experiment.py`: several hundred;
- `taste_gallery.py`: several hundred;
- route wiring in `app.py`: a few hundred.

A reducer/executor/job/projection split should remove repeated command scaffolding and private-service calls. A plausible target is:

```text
command reducers + executor + treatment policies + gallery use case
≈ 45–60% of current orchestration lines
```

This is a 1.7–2.2× reduction in that slice, with a larger quality improvement than the raw line count suggests.

### Frontend

The ordinary UI, emergent UI, concept controllers, and gallery repeat session/API/SSE/exposure/history machinery. Consolidation can plausibly remove 40–55% of controller lines.

### Whole repository

A 2× whole-repository reduction requires retiring or moving the legacy browser concept system and persistent atlas into an explicitly frozen `legacy_t0/` boundary. A 5× reduction would require deleting product surface, tests, and documentation; it should not be set as a refactor goal.

## 6. What should remain separate

Do not over-share these simply to reduce line count:

- taste inference versus branch utility inference;
- fixed-root vote loop versus cross-seed gallery;
- pure command reduction versus renderer execution;
- persistent facts versus cached projections;
- renderer-independent action types versus model-specific conditioning adapters.

The desired codebase is not “no `if` statements.” It is **branching once on a closed typed sum**, followed by straight-line code for each case, rather than rediscovering state shape through defensive checks in every layer.

## Verdict

**Prototype slop:** substantial but localized.  
**Architecture quality:** useful seams beneath an oversized mutable service.  
**Reduction opportunity:** 2–3× in orchestration and ~2× in frontend controllers; less across the whole repository unless legacy treatments are retired.  
**Priority:** correctness boundaries first, then reduction. Refactoring the current semantics before fixing persistence and model ownership would make the bugs cleaner, not remove them.
