# Track BUG-1 — Persistence, Idempotency, Concurrency, and Recovery

## Severity summary

| Severity | Finding |
|---|---|
| Critical | emergent preference fact can be permanently lost after the base command commits |
| High | anchor-win learner updates are not checkpointed and disappear on history restore |
| High | command mutation and command-result receipt are not one transaction |
| High | process crash during `new_world` can leave a session permanently transitioning |
| High | cancelling an asyncio render task does not cancel its worker thread/GPU work |
| Medium | event/request idempotency does not bind a request ID to the complete payload |
| Medium | persistent atlas is updated by navigation and emergent-treatment interactions, confounding experiments |

## 1. Critical — lost emergent-taste vote after base commit

### Code path

[`EmergentTasteExperiment.commit_candidate`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/emergent_experiment.py) performs:

```python
before = await self.service.get_snapshot(session_id)
draft = self._build_observation(before, payload, ...)
draft = draft.with_prediction_receipts(...)

result = await self.service.commit_candidate(...)
# base session/event/projection is now committed

observation = draft.with_result_branch(result["current_branch_node_id"])
await self._append_observation(...)
```

The same structure exists for `none_of_these`.

### Failure

If the process dies after `service.commit_candidate` returns internally but before `_append_observation` commits:

- the chosen design and legacy posterior are durable;
- the base command may have a cached result;
- no emergent choice event exists;
- retry cannot reconstruct the old slate from the now-current session;
- the taste model permanently misses the vote.

This violates the treatment's central claim that every qualified vote is predicted before training and replayable.

### Required fix

Use one of two designs:

**A. Single physical transaction**

Commit in one SQLite transaction:

```text
base session projection
base command event
emergent choice event
taste projection cursor
command result
```

**B. Event-first recoverable protocol**

```text
PreferenceChoicePending(full immutable slate and prediction receipts)
base mutation
PreferenceChoiceFinalized(result checkpoint)
```

On restart, pending events are reconciled against the base command event. The pending fact must already contain everything needed to finalize.

## 2. High — `None fit` updates disappear on history restore

[`ArtOptimizerService.reroll`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py) can update:

```text
active_posterior
search radius
reroll counters
planner step
```

without changing `current_design_id` and without creating a new `BranchNode`.

[`restore`](https://github.com/nbardy/art-optimizer/blob/893e4049105ac56a829edadface3a35a61d087d5/art_optimizer/service.py) later loads `branch.posterior` and `branch.search_state`. That branch contains the state from the last navigation checkpoint, not the post-reroll state.

### Reproduction sketch

1. commit candidate A, creating branch B;
2. use `None fit` several times, updating the learner at B;
3. navigate to another branch;
4. restore B;
5. learner state returns to the original B snapshot; all non-navigation observations vanish from the active branch state.

### Fix

Every preference-bearing command creates an immutable checkpoint, even if it points to the same design:

```python
BranchNode(
    design_id=current_design_id,
    parent_branch_node_id=current_branch_node_id,
    posterior=new_posterior,
    search_state=new_search_state,
)
```

Or separate `DesignNavigationNode` from `PreferenceCheckpoint` explicitly.

## 3. High — command receipts are not crash-atomic

Base commands use:

1. `record_session_event` — event and session projection in one transaction;
2. publish/start next round;
3. `save_command_result` — a later transaction.

A crash between steps 1 and 3 leaves the mutation committed without the idempotent response receipt.

A retry may:

- receive a stale-mutation conflict;
- fail because the candidate/round is no longer active;
- not return the original successful response.

The command-result row should commit with the authoritative mutation, or the event should carry a deterministic response that can be rebuilt.

## 4. High — `new_world` can remain stuck after process death

`new_world` first persists:

```text
status = transitioning
transition_id = request_id
active round cancelled
```

then renders outside the lock and commits the new world later.

If the process stops during rendering, `_repair_loaded_state` does not detect or resolve a stranded `transition_id`. On reload the session can remain in `transitioning` indefinitely.

### Fix

Persist a typed render job and recover it, or mark transitions with a lease/state machine:

```text
requested -> running -> completed | failed | abandoned
```

Startup should requeue or fail expired jobs deterministically.

## 5. High — cancellation does not cancel rendering

`_cancel_stale_tasks` cancels `asyncio.Task` objects created around `_render_candidate`. But `_render_candidate` calls:

```python
await asyncio.to_thread(self.renderer.render, ...)
```

Cancelling the coroutine does not terminate the underlying thread. For a local Diffusers renderer:

- GPU generation continues;
- the renderer lock remains occupied;
- a supposedly cancelled old slate can delay the new slate;
- the thread may still write an artifact;
- cleanup logic in the cancelled coroutine may never run.

The runtime needs a bounded render-job executor with cooperative cancellation at boundaries the renderer actually supports. Where cancellation is impossible, state should say “obsolete, allowed to finish,” not “cancelled.”

## 6. Medium — request IDs are not bound to payload digests

Gallery generation and activation search previous events by `request_id` and kind. Reusing a request ID with different:

- taste ID;
- strengths;
- row count;
- seed nonce;
- gallery ID;
- cell ID;

returns the first result rather than a conflict.

The base `command_results` table checks command kind but not canonical payload digest.

### Fix

Persist:

```text
request_id
command_kind
command_payload_digest
result
```

Same ID + same digest is idempotent. Same ID + different digest is a conflict.

## 7. Medium — emergent treatment still mutates persistent atlas

A candidate commit in the emergent UI delegates to the base service, which calls `_add_atlas_evidence(selected_design, "commit")`. History restore adds `revisit` evidence. The initial world and candidate planner may then use atlas guidance.

This means the emergent-taste experiment is changed by a separate online clustering model and its historical interactions. It also means simply revisiting an image repeatedly can increase durable preference mass.

The treatment policy should explicitly disable atlas writes and reads for a clean ablation, or record atlas influence as a declared experimental factor.

## 8. Medium — event store is serialized per method, not per use case

`EventStore` uses a process-local `RLock`, and each method opens a new SQLite connection/transaction. Multi-step commands therefore cannot express a single use-case transaction. Multiple workers/processes would not share the Python lock.

A repository method should own each complete transaction, for example:

```python
commit_choice_command(
    expected_projection_version,
    base_event,
    new_session_projection,
    preference_event,
    command_receipt,
)
```

Use `BEGIN IMMEDIATE` and optimistic version checks in SQLite, not only in-memory locks.

## 9. Tests required

Add failure-injection tests at every durable boundary:

- crash after pending event;
- crash after base mutation;
- crash before command receipt;
- retry after each crash;
- process restart with stranded world transition;
- restore after several anchor-win updates;
- two concurrent requests with same ID/same payload;
- same ID/different payload;
- concurrent workers updating the same session.

The expected invariant is:

```text
one logical command -> zero or one authoritative mutation,
                       one recoverable fact,
                       one stable response
```

## Verdict

The persistence layer is sufficient for a single-process demo, but the emergent choice path is not yet trustworthy as scientific evidence. Fix the lost-vote and checkpoint bugs before changing the mathematical model or making it authoritative.
