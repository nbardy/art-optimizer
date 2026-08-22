from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

import numpy as np

from .atlas import AtlasGuidance, PersistentPreferenceAtlas
from .config import Settings
from .domain import (
    BranchNode,
    CandidateRound,
    CommandPayload,
    CommitPayload,
    CreateSessionRequest,
    DesignState,
    ExposurePayload,
    FavoritePayload,
    NewWorldPayload,
    RestorePayload,
    SearchState,
    SessionState,
    WorldState,
    new_id,
)
from .event_store import EventStore
from .planner import CandidatePlanner, PlannerContext
from .preference import BayesianChoiceModel
from .renderer import ProceduralRenderer
from .rendering import ImageRenderer, artifact_manifest_path


class NotFoundError(KeyError):
    pass


class ConflictError(RuntimeError):
    pass


class OperationError(RuntimeError):
    pass


@dataclass(slots=True)
class SessionRuntime:
    state: SessionState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    command_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    render_tasks: set[asyncio.Task[Any]] = field(default_factory=set)


class ArtOptimizerService:
    """Authoritative interaction state machine with injected experiment seams.

    The service owns session transitions exactly once. Renderers, planners, stores,
    and persistent-memory implementations are dependencies rather than subclasses,
    so model/UI experiments cannot fork the branch/world semantics accidentally.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        renderer: ImageRenderer | None = None,
        planner: CandidatePlanner | None = None,
        store: EventStore | None = None,
        atlas: PersistentPreferenceAtlas | None = None,
    ) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self.store = store or EventStore(settings.database_path)
        self.renderer = renderer or ProceduralRenderer(
            settings.artifacts_dir, settings.renderer_size
        )
        capabilities = self.renderer.capabilities()
        if capabilities.action_dimension != settings.action_dimension:
            raise ValueError("renderer and configured action dimensions do not match")
        self.planner = planner or CandidatePlanner(capabilities.action_dimension)
        self.atlas = atlas or PersistentPreferenceAtlas(self.store.load_atlas())
        self._atlas_lock = asyncio.Lock()
        self._runtime_load_lock = asyncio.Lock()
        self._sessions: dict[str, SessionRuntime] = {}

    async def shutdown(self) -> None:
        runtimes = list(self._sessions.values())
        for runtime in runtimes:
            await self._cancel_stale_tasks(runtime)
            runtime.subscribers.clear()

    async def create_session(self, request: CreateSessionRequest) -> dict[str, Any]:
        session_id = new_id("session")
        seed = request.seed if request.seed is not None else secrets.randbits(62)
        rng = np.random.default_rng(seed)

        async with self._atlas_lock:
            guidance = self.atlas.choose_guidance(
                rng,
                control_basis_revision=self.renderer.control_basis_revision,
                action_dimension=self.settings.action_dimension,
            )

        action = rng.normal(0.0, 0.28, size=self.settings.action_dimension)
        if guidance.action_bias is not None:
            action = 0.68 * guidance.action_bias + 0.32 * action
        action = np.clip(action, -0.78, 0.78)

        world_id = new_id("world")
        root_design_id = new_id("design")
        artifact = await asyncio.to_thread(
            self.renderer.render,
            design_id=root_design_id,
            seed=seed,
            prompt=request.prompt,
            action=action,
        )
        root_design = self._design_from_artifact(
            design_id=root_design_id,
            world_id=world_id,
            seed=seed,
            prompt=request.prompt,
            action=action,
            artifact=artifact,
        )

        model = BayesianChoiceModel(self.settings.action_dimension)
        search_state = SearchState()
        root_branch = BranchNode(
            branch_node_id=new_id("branch"),
            design_id=root_design_id,
            posterior=model.snapshot(),
            search_state=search_state.model_copy(deep=True),
        )
        world = WorldState(
            world_id=world_id,
            seed=seed,
            prompt=request.prompt,
            root_design_id=root_design_id,
            renderer_revision=self.renderer.revision,
            control_basis_revision=self.renderer.control_basis_revision,
            initialization_mode="taste_guided",
            initialization_action=action.astype(float).tolist(),
            atlas_component_id=guidance.component_id,
            atlas_bias_action=(
                guidance.action_bias.tolist() if guidance.action_bias is not None else None
            ),
        )
        state = SessionState(
            session_id=session_id,
            prompt=request.prompt,
            world=world,
            worlds={world_id: world},
            designs={root_design_id: root_design},
            branches={root_branch.branch_node_id: root_branch},
            current_design_id=root_design_id,
            current_branch_node_id=root_branch.branch_node_id,
            active_posterior=model.snapshot(),
            search_state=search_state,
            history=[root_branch.branch_node_id],
        )
        runtime = SessionRuntime(state=state)
        self._sessions[session_id] = runtime

        self.store.record_session_event(
            state,
            "world_created",
            {
                "world_id": world_id,
                "root_design_id": root_design_id,
                "seed": seed,
                "prompt": request.prompt,
                "mode": "taste_guided",
                "initial_action": action.astype(float).tolist(),
                "atlas_component_id": guidance.component_id,
                "atlas_mode": guidance.mode,
                "renderer_revision": self.renderer.revision,
                "control_basis_revision": self.renderer.control_basis_revision,
            },
        )
        await self._start_round(runtime)
        return await self._snapshot(runtime)

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        return await self._snapshot(runtime)

    async def stream(self, session_id: str) -> AsyncIterator[str]:
        runtime = await self._get_runtime(session_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        async with self._atlas_lock:
            atlas_summary = self.atlas.summary()
        async with runtime.lock:
            runtime.subscribers.add(queue)
            initial = self._public_snapshot(runtime.state, atlas_summary)
        await queue.put(
            {
                "type": "session.snapshot",
                "id": initial["version"],
                "payload": initial,
            }
        )
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    data = json.dumps(event["payload"], separators=(",", ":"))
                    yield (
                        f"id: {event['id']}\n"
                        f"event: {event['type']}\n"
                        f"data: {data}\n\n"
                    )
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            async with runtime.lock:
                runtime.subscribers.discard(queue)

    async def commit_candidate(
        self,
        session_id: str,
        candidate_id: str,
        payload: CommitPayload,
    ) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.command_lock:
            cached = self._cached_command(session_id, payload.request_id, "commit_candidate")
            if cached is not None:
                return cached

            async with runtime.lock:
                state = runtime.state
                self._validate_expected_mutation(state, payload)
                round_state = state.active_round
                if round_state is None or round_state.status in {"closed", "cancelled"}:
                    raise ConflictError("there is no active round")

                candidates = round_state.candidates
                chosen_index = next(
                    (
                        index
                        for index, candidate in enumerate(candidates)
                        if candidate.candidate_id == candidate_id
                    ),
                    None,
                )
                if chosen_index is None:
                    raise NotFoundError("candidate not found in active round")
                chosen = candidates[chosen_index]
                if chosen.status != "ready" or chosen.design_id is None:
                    raise ConflictError("candidate is not ready")

                exposed = set(payload.exposed_candidate_ids)
                exposed.add(candidate_id)
                exposure_mask = np.asarray(
                    [
                        candidate.candidate_id in exposed and candidate.status == "ready"
                        for candidate in candidates
                    ],
                    dtype=bool,
                )
                effective_exposed = [
                    candidate.candidate_id
                    for candidate, visible in zip(candidates, exposure_mask, strict=True)
                    if visible
                ]
                model = BayesianChoiceModel(self.settings.action_dimension, state.active_posterior)
                model.update_choice(
                    anchor_action=np.asarray(state.current_design().action, dtype=np.float64),
                    candidate_actions=np.asarray(
                        [candidate.action for candidate in candidates], dtype=np.float64
                    ),
                    chosen_candidate_index=chosen_index,
                    exposure_mask=exposure_mask,
                    weight=1.0,
                )

                previous_branch_id = state.current_branch_node_id
                state.search_state.radius = max(0.26, state.search_state.radius * 0.90)
                state.search_state.consecutive_commits += 1
                state.search_state.consecutive_rerolls = 0
                state.search_state.planner_step += 1
                state.active_posterior = model.snapshot()
                state.current_design_id = chosen.design_id
                new_branch = BranchNode(
                    branch_node_id=new_id("branch"),
                    design_id=chosen.design_id,
                    parent_branch_node_id=previous_branch_id,
                    posterior=state.active_posterior.model_copy(deep=True),
                    search_state=state.search_state.model_copy(deep=True),
                )
                state.branches[new_branch.branch_node_id] = new_branch
                state.current_branch_node_id = new_branch.branch_node_id
                self._remember_branch(state, new_branch.branch_node_id)
                round_state.status = "closed"
                state.active_round = None
                state.status = "generating"
                state.touch(mutation=True)

                selected_design = state.designs[chosen.design_id]
                self.store.record_session_event(
                    state,
                    "candidate_committed",
                    {
                        "request_id": payload.request_id,
                        "round_id": round_state.round_id,
                        "candidate_id": candidate_id,
                        "design_id": chosen.design_id,
                        "exposed_candidate_ids": effective_exposed,
                        "branch_node_id": new_branch.branch_node_id,
                        "mutation_version": state.mutation_version,
                    },
                )

            await self._cancel_stale_tasks(runtime)
            await self._add_atlas_evidence(selected_design, "commit")
            await self._publish_snapshot(runtime)
            await self._start_round(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(
                session_id, payload.request_id, "commit_candidate", result
            )
            return result

    async def reroll(self, session_id: str, payload: ExposurePayload) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.command_lock:
            cached = self._cached_command(session_id, payload.request_id, "reroll")
            if cached is not None:
                return cached

            async with runtime.lock:
                state = runtime.state
                self._validate_expected_mutation(state, payload)
                round_state = state.active_round
                if round_state is None or round_state.status in {"closed", "cancelled"}:
                    raise ConflictError("there is no active round")

                exposed = set(payload.exposed_candidate_ids)
                candidates = round_state.candidates
                exposure_mask = np.asarray(
                    [
                        candidate.candidate_id in exposed and candidate.status == "ready"
                        for candidate in candidates
                    ],
                    dtype=bool,
                )
                effective_exposed = [
                    candidate.candidate_id
                    for candidate, visible in zip(candidates, exposure_mask, strict=True)
                    if visible
                ]
                exposed_count = int(exposure_mask.sum())

                if exposed_count >= 2:
                    model = BayesianChoiceModel(
                        self.settings.action_dimension, state.active_posterior
                    )
                    model.update_choice(
                        anchor_action=np.asarray(state.current_design().action, dtype=np.float64),
                        candidate_actions=np.asarray(
                            [candidate.action for candidate in candidates], dtype=np.float64
                        ),
                        chosen_candidate_index=None,
                        exposure_mask=exposure_mask,
                        weight=0.35,
                    )
                    state.active_posterior = model.snapshot()
                    event_kind = "round_rerolled"
                else:
                    event_kind = "round_skipped"

                state.search_state.radius = min(
                    1.25, state.search_state.radius * 1.22 + 0.025
                )
                state.search_state.consecutive_rerolls += 1
                state.search_state.consecutive_commits = 0
                state.search_state.planner_step += 1
                round_state.status = "closed"
                state.active_round = None
                state.status = "generating"
                state.touch(mutation=True)
                self.store.record_session_event(
                    state,
                    event_kind,
                    {
                        "request_id": payload.request_id,
                        "round_id": round_state.round_id,
                        "exposed_candidate_ids": effective_exposed,
                        "exposed_count": exposed_count,
                        "radius": state.search_state.radius,
                        "mutation_version": state.mutation_version,
                    },
                )

            await self._cancel_stale_tasks(runtime)
            await self._publish_snapshot(runtime)
            await self._start_round(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(session_id, payload.request_id, "reroll", result)
            return result

    async def favorite(
        self,
        session_id: str,
        design_id: str,
        payload: FavoritePayload,
    ) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.command_lock:
            cached = self._cached_command(session_id, payload.request_id, "favorite")
            if cached is not None:
                return cached

            changed = False
            async with runtime.lock:
                state = runtime.state
                if design_id not in state.designs:
                    raise NotFoundError("design not found")
                design = state.designs[design_id]
                if payload.favorite and design_id not in state.favorites:
                    state.favorites.append(design_id)
                    changed = True
                elif not payload.favorite and design_id in state.favorites:
                    state.favorites.remove(design_id)
                    changed = True
                if changed:
                    state.touch()
                    self.store.record_session_event(
                        state,
                        "design_favorited" if payload.favorite else "design_unfavorited",
                        {"request_id": payload.request_id, "design_id": design_id},
                    )

            if changed:
                if payload.favorite:
                    await self._add_atlas_evidence(design, "favorite")
                else:
                    async with self._atlas_lock:
                        self.atlas.retract_favorite(design_id)
                        self.store.save_atlas(self.atlas.state)
                await self._publish_snapshot(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(session_id, payload.request_id, "favorite", result)
            return result

    async def new_world(
        self,
        session_id: str,
        payload: NewWorldPayload,
    ) -> dict[str, Any]:
        """Create a new stochastic root through one shared transition path.

        Only root-action selection varies by policy. Transition, rendering,
        persistence, failure recovery, and round creation remain identical across
        `taste_guided`, `neutral`, and `composition` so UI experiments cannot
        diverge in hidden state semantics.
        """

        self._validate_world_payload(payload)
        runtime = await self._get_runtime(session_id)
        async with runtime.command_lock:
            cached = self._cached_command(session_id, payload.request_id, "new_world")
            if cached is not None:
                return cached

            async with runtime.lock:
                state = runtime.state
                self._validate_expected_mutation(state, payload)
                if state.active_round is not None:
                    state.active_round.status = "cancelled"
                    state.active_round = None
                state.status = "transitioning"
                state.transition_id = payload.request_id
                state.touch(mutation=True)
                prompt = state.prompt
                self.store.record_session_event(
                    state,
                    "new_world_requested",
                    {
                        "request_id": payload.request_id,
                        "source_design_id": state.current_design_id,
                        "mode": payload.mode,
                        "target_action": payload.target_action,
                        "mutation_version": state.mutation_version,
                    },
                )

            await self._cancel_stale_tasks(runtime)
            await self._publish_snapshot(runtime)

            seed = secrets.randbits(62)
            rng = np.random.default_rng(seed)
            guidance = await self._world_guidance(payload, rng)
            action = self._root_action(payload, rng, guidance.action_bias)
            world_id = new_id("world")
            root_design_id = new_id("design")
            try:
                artifact = await asyncio.to_thread(
                    self.renderer.render,
                    design_id=root_design_id,
                    seed=seed,
                    prompt=prompt,
                    action=action,
                )
            except Exception as error:
                async with runtime.lock:
                    state = runtime.state
                    if state.transition_id == payload.request_id:
                        state.transition_id = None
                        state.status = "generating"
                        state.touch()
                        self.store.record_session_event(
                            state,
                            "new_world_failed",
                            {
                                "request_id": payload.request_id,
                                "mode": payload.mode,
                                "error": str(error),
                            },
                        )
                await self._publish_snapshot(runtime)
                await self._start_round(runtime)
                raise OperationError(f"failed to create a new world: {error}") from error

            design = self._design_from_artifact(
                design_id=root_design_id,
                world_id=world_id,
                seed=seed,
                prompt=prompt,
                action=action,
                artifact=artifact,
            )
            model = BayesianChoiceModel(self.settings.action_dimension)
            search_state = SearchState()
            branch = BranchNode(
                branch_node_id=new_id("branch"),
                design_id=root_design_id,
                posterior=model.snapshot(),
                search_state=search_state.model_copy(deep=True),
            )
            world = WorldState(
                world_id=world_id,
                seed=seed,
                prompt=prompt,
                root_design_id=root_design_id,
                renderer_revision=self.renderer.revision,
                control_basis_revision=self.renderer.control_basis_revision,
                initialization_mode=payload.mode,
                initialization_action=action.astype(float).tolist(),
                atlas_component_id=guidance.component_id,
                atlas_bias_action=(
                    guidance.action_bias.tolist() if guidance.action_bias is not None else None
                ),
            )

            async with runtime.lock:
                state = runtime.state
                if state.transition_id != payload.request_id:
                    artifact.path.unlink(missing_ok=True)
                    artifact_manifest_path(artifact.path).unlink(missing_ok=True)
                    raise ConflictError("new-world transition was superseded")
                state.world = world
                state.worlds[world_id] = world
                state.designs[root_design_id] = design
                state.branches[branch.branch_node_id] = branch
                state.current_design_id = root_design_id
                state.current_branch_node_id = branch.branch_node_id
                state.active_posterior = model.snapshot()
                state.search_state = search_state
                self._remember_branch(state, branch.branch_node_id)
                state.transition_id = None
                state.status = "generating"
                state.touch()
                self.store.record_session_event(
                    state,
                    "world_created",
                    {
                        "request_id": payload.request_id,
                        "world_id": world_id,
                        "root_design_id": root_design_id,
                        "seed": seed,
                        "mode": payload.mode,
                        "initial_action": action.astype(float).tolist(),
                        "atlas_component_id": guidance.component_id,
                        "atlas_mode": guidance.mode,
                        "renderer_revision": self.renderer.revision,
                        "control_basis_revision": self.renderer.control_basis_revision,
                    },
                )

            await self._publish_snapshot(runtime)
            await self._start_round(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(session_id, payload.request_id, "new_world", result)
            return result

    async def restore(
        self,
        session_id: str,
        branch_node_id: str,
        payload: RestorePayload,
    ) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.command_lock:
            cached = self._cached_command(session_id, payload.request_id, "restore")
            if cached is not None:
                return cached

            async with runtime.lock:
                state = runtime.state
                self._validate_expected_mutation(state, payload)
                if branch_node_id not in state.branches:
                    raise NotFoundError("history checkpoint not found")
                branch = state.branches[branch_node_id]
                design = state.designs[branch.design_id]
                world = state.worlds.get(design.world_id)
                if world is None:
                    world = self._world_from_design(state, design)
                    state.worlds[world.world_id] = world
                if state.active_round is not None:
                    state.active_round.status = "cancelled"
                state.active_round = None
                state.world = world
                state.prompt = world.prompt
                state.current_branch_node_id = branch_node_id
                state.current_design_id = branch.design_id
                state.active_posterior = branch.posterior.model_copy(deep=True)
                state.search_state = branch.search_state.model_copy(deep=True)
                state.search_state.planner_step += 1
                self._remember_branch(state, branch_node_id)
                state.status = "generating"
                state.touch(mutation=True)
                self.store.record_session_event(
                    state,
                    "history_state_restored",
                    {
                        "request_id": payload.request_id,
                        "branch_node_id": branch_node_id,
                        "design_id": branch.design_id,
                        "world_id": world.world_id,
                        "mutation_version": state.mutation_version,
                    },
                )

            await self._cancel_stale_tasks(runtime)
            await self._add_atlas_evidence(design, "revisit")
            await self._publish_snapshot(runtime)
            await self._start_round(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(session_id, payload.request_id, "restore", result)
            return result

    async def events(self, session_id: str) -> list[dict[str, Any]]:
        await self._get_runtime(session_id)
        return self.store.list_events(session_id)

    async def _start_round(self, runtime: SessionRuntime) -> None:
        async with runtime.lock:
            state = runtime.state
            if state.active_round is not None and state.active_round.status not in {
                "closed",
                "cancelled",
            }:
                return
            anchor = state.current_design().model_copy(deep=True)
            posterior = state.active_posterior.model_copy(deep=True)
            search_state = state.search_state.model_copy(deep=True)
            world = state.world.model_copy(deep=True)
            branch_node_id = state.current_branch_node_id
            mutation_version = state.mutation_version
            seed_material = (
                f"{state.session_id}:{world.world_id}:{branch_node_id}:"
                f"{search_state.planner_step}:{mutation_version}"
            ).encode("utf-8")
            planner_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "little")
            planner_seed &= (1 << 63) - 1

        async with self._atlas_lock:
            alternate = self.atlas.alternate_action_bias(
                world.atlas_component_id,
                control_basis_revision=world.control_basis_revision,
                action_dimension=self.settings.action_dimension,
            )

        model = BayesianChoiceModel(self.settings.action_dimension, posterior)
        rng = np.random.default_rng(planner_seed)
        atlas_bias = (
            np.asarray(world.atlas_bias_action, dtype=np.float64)
            if world.atlas_bias_action is not None
            else None
        )
        try:
            proposals = self.planner.propose(
                model=model,
                context=PlannerContext(
                    anchor_action=np.asarray(anchor.action, dtype=np.float64),
                    search_state=search_state,
                    atlas_bias_action=atlas_bias,
                    alternate_atlas_action=alternate,
                ),
                rng=rng,
            )
        except Exception as error:
            async with runtime.lock:
                state = runtime.state
                if (
                    state.mutation_version == mutation_version
                    and state.current_branch_node_id == branch_node_id
                ):
                    state.status = "error"
                    state.touch()
                    self.store.record_session_event(
                        state,
                        "candidate_round_failed",
                        {"error": str(error), "planner_seed": planner_seed},
                    )
            await self._publish_snapshot(runtime)
            raise

        async with runtime.lock:
            state = runtime.state
            if (
                state.mutation_version != mutation_version
                or state.current_branch_node_id != branch_node_id
                or state.current_design_id != anchor.design_id
                or state.active_round is not None
            ):
                return
            round_state = CandidateRound(
                round_id=new_id("round"),
                parent_design_id=anchor.design_id,
                parent_branch_node_id=branch_node_id,
                branch_version=mutation_version,
                planner_seed=planner_seed,
                candidates=proposals,
            )
            state.active_round = round_state
            state.status = "generating"
            state.touch()
            self.store.record_session_event(
                state,
                "candidate_round_proposed",
                {
                    "round_id": round_state.round_id,
                    "parent_design_id": anchor.design_id,
                    "branch_version": mutation_version,
                    "planner_seed": planner_seed,
                    "roles": [proposal.role for proposal in proposals],
                    "actions": [proposal.action for proposal in proposals],
                    "planner_revision": self.planner.revision,
                },
            )
            for proposal in proposals:
                task = asyncio.create_task(
                    self._render_candidate(runtime, round_state.round_id, proposal.candidate_id)
                )
                runtime.render_tasks.add(task)
                task.add_done_callback(runtime.render_tasks.discard)

        await self._publish_snapshot(runtime)

    async def _render_candidate(
        self,
        runtime: SessionRuntime,
        round_id: str,
        candidate_id: str,
    ) -> None:
        artifact = None
        try:
            async with runtime.lock:
                state = runtime.state
                round_state = state.active_round
                if round_state is None or round_state.round_id != round_id:
                    return
                candidate = next(
                    (item for item in round_state.candidates if item.candidate_id == candidate_id),
                    None,
                )
                if candidate is None:
                    return
                candidate.status = "rendering"
                parent_design_id = round_state.parent_design_id
                world = state.world.model_copy(deep=True)
                action = np.asarray(candidate.action, dtype=np.float64)
                slot = candidate.slot
                stable_design_id = candidate.design_id or self._candidate_design_id(
                    world.world_id, candidate_id
                )
                candidate.design_id = stable_design_id
                state.touch()
                self.store.save_session(state)

            await self._publish_snapshot(runtime)
            await asyncio.sleep(0.055 * slot)
            artifact = await asyncio.to_thread(
                self.renderer.render,
                design_id=stable_design_id,
                seed=world.seed,
                prompt=world.prompt,
                action=action,
            )

            async with runtime.lock:
                state = runtime.state
                round_state = state.active_round
                if round_state is None or round_state.round_id != round_id:
                    artifact.path.unlink(missing_ok=True)
                    artifact_manifest_path(artifact.path).unlink(missing_ok=True)
                    return
                candidate = next(
                    (item for item in round_state.candidates if item.candidate_id == candidate_id),
                    None,
                )
                if candidate is None:
                    artifact.path.unlink(missing_ok=True)
                    artifact_manifest_path(artifact.path).unlink(missing_ok=True)
                    return
                design = self._design_from_artifact(
                    design_id=stable_design_id,
                    world_id=world.world_id,
                    parent_design_id=parent_design_id,
                    source_candidate_id=candidate_id,
                    seed=world.seed,
                    prompt=world.prompt,
                    action=action,
                    artifact=artifact,
                )
                state.designs[stable_design_id] = design
                candidate.status = "ready"
                candidate.design_id = stable_design_id
                candidate.image_url = design.image_url
                candidate.error = None

                complete = all(
                    item.status in {"ready", "failed"} for item in round_state.candidates
                )
                if complete:
                    round_state.status = "ready"
                    state.status = (
                        "ready"
                        if any(item.status == "ready" for item in round_state.candidates)
                        else "error"
                    )
                state.touch()
                self.store.record_session_event(
                    state,
                    "candidate_ready",
                    {
                        "round_id": round_id,
                        "candidate_id": candidate_id,
                        "design_id": stable_design_id,
                        "slot": candidate.slot,
                        "image_digest": artifact.digest,
                    },
                )
            await self._publish_snapshot(runtime)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # pragma: no cover - defensive worker boundary
            async with runtime.lock:
                state = runtime.state
                round_state = state.active_round
                if round_state is None or round_state.round_id != round_id:
                    return
                candidate = next(
                    (item for item in round_state.candidates if item.candidate_id == candidate_id),
                    None,
                )
                if candidate is None:
                    return
                candidate.status = "failed"
                candidate.error = str(error)
                if all(
                    item.status in {"ready", "failed"} for item in round_state.candidates
                ):
                    round_state.status = "ready"
                    state.status = (
                        "ready"
                        if any(item.status == "ready" for item in round_state.candidates)
                        else "error"
                    )
                state.touch()
                self.store.record_session_event(
                    state,
                    "candidate_failed",
                    {"round_id": round_id, "candidate_id": candidate_id, "error": str(error)},
                )
            await self._publish_snapshot(runtime)

    async def _add_atlas_evidence(self, design: DesignState, kind: str) -> None:
        async with self._atlas_lock:
            self.atlas.add_evidence(
                design_id=design.design_id,
                feature_vector=design.feature_vector,
                action=design.action,
                kind=kind,
                feature_revision=design.feature_revision,
                control_basis_revision=design.control_basis_revision,
                renderer_revision=design.renderer_revision,
            )
            self.store.save_atlas(self.atlas.state)

    async def _get_runtime(self, session_id: str) -> SessionRuntime:
        runtime = self._sessions.get(session_id)
        if runtime is not None:
            return runtime
        async with self._runtime_load_lock:
            runtime = self._sessions.get(session_id)
            if runtime is not None:
                return runtime
            state = self.store.load_session(session_id)
            if state is None:
                raise NotFoundError("session not found")
            changed = self._repair_loaded_state(state)
            runtime = SessionRuntime(state=state)
            self._sessions[session_id] = runtime

            round_state = state.active_round
            if round_state is not None and round_state.status in {"rendering", "ready"}:
                needs_render = False
                for candidate in round_state.candidates:
                    if candidate.status == "ready" and candidate.design_id:
                        design = state.designs.get(candidate.design_id)
                        if design is not None and Path(design.image_path).exists():
                            continue
                    if candidate.status in {"queued", "rendering", "ready"}:
                        candidate.status = "queued"
                        candidate.image_url = None
                        needs_render = True
                        task = asyncio.create_task(
                            self._render_candidate(
                                runtime, round_state.round_id, candidate.candidate_id
                            )
                        )
                        runtime.render_tasks.add(task)
                        task.add_done_callback(runtime.render_tasks.discard)
                if needs_render:
                    round_state.status = "rendering"
                    state.status = "generating"
                    changed = True
            if changed:
                self.store.save_session(state)
            return runtime

    async def _cancel_stale_tasks(self, runtime: SessionRuntime) -> None:
        tasks = [task for task in runtime.render_tasks if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        runtime.render_tasks.difference_update(tasks)

    async def _snapshot(self, runtime: SessionRuntime) -> dict[str, Any]:
        async with self._atlas_lock:
            atlas_summary = self.atlas.summary()
        async with runtime.lock:
            return self._public_snapshot(runtime.state, atlas_summary)

    async def _publish_snapshot(self, runtime: SessionRuntime) -> None:
        payload = await self._snapshot(runtime)
        event = {
            "type": "session.snapshot",
            "id": payload["version"],
            "payload": payload,
        }
        async with runtime.lock:
            subscribers = list(runtime.subscribers)
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def _public_snapshot(
        self,
        state: SessionState,
        atlas_summary: dict[str, object],
    ) -> dict[str, Any]:
        current = state.current_design()
        round_payload = state.active_round.model_dump(mode="json") if state.active_round else None
        history_items = []
        for branch_id in state.history[-10:]:
            branch = state.branches.get(branch_id)
            if branch is None:
                continue
            design = state.designs.get(branch.design_id)
            if design is None:
                continue
            history_items.append(
                {
                    "branch_node_id": branch.branch_node_id,
                    "design_id": design.design_id,
                    "world_id": design.world_id,
                    "image_url": design.image_url,
                    "favorite": design.design_id in state.favorites,
                    "current": branch.branch_node_id == state.current_branch_node_id,
                    "created_at": branch.created_at,
                }
            )
        return {
            "session_id": state.session_id,
            "version": state.version,
            "mutation_version": state.mutation_version,
            "prompt": state.prompt,
            "status": state.status,
            "transition_id": state.transition_id,
            "world": state.world.model_dump(mode="json"),
            "current_design": current.model_dump(mode="json"),
            "current_branch_node_id": state.current_branch_node_id,
            "active_round": round_payload,
            "favorites": state.favorites,
            "history": history_items,
            "history_total": len(state.history),
            "search": state.search_state.model_dump(mode="json"),
            "learner": {
                "observation_count": state.active_posterior.observation_count,
                "feature_dimension": state.active_posterior.feature_dimension,
            },
            "renderer": self.renderer.capabilities().__dict__,
            "atlas": atlas_summary,
        }

    def _cached_command(
        self, session_id: str, request_id: str, kind: str
    ) -> dict[str, Any] | None:
        try:
            return self.store.load_command_result(session_id, request_id, kind)
        except ValueError as error:
            raise ConflictError(str(error)) from error

    @staticmethod
    def _validate_expected_mutation(
        state: SessionState, payload: CommandPayload
    ) -> None:
        expected = payload.resolved_expected_mutation_version()
        if expected is not None and expected != state.mutation_version:
            raise ConflictError(
                f"session mutation version is stale: expected {expected}, "
                f"current {state.mutation_version}"
            )

    def _validate_world_payload(self, payload: NewWorldPayload) -> None:
        if payload.mode != "composition":
            return
        if payload.target_action is None or len(payload.target_action) != self.settings.action_dimension:
            raise ConflictError(
                f"composition requires {self.settings.action_dimension} controls"
            )

    async def _world_guidance(
        self,
        payload: NewWorldPayload,
        rng: np.random.Generator,
    ) -> AtlasGuidance:
        if payload.mode != "taste_guided":
            return AtlasGuidance(component_id=None, action_bias=None, mode=payload.mode)
        async with self._atlas_lock:
            return self.atlas.choose_guidance(
                rng,
                control_basis_revision=self.renderer.control_basis_revision,
                action_dimension=self.settings.action_dimension,
            )

    def _root_action(
        self,
        payload: NewWorldPayload,
        rng: np.random.Generator,
        atlas_bias: np.ndarray | None,
    ) -> np.ndarray:
        if payload.mode == "neutral":
            return np.zeros(self.settings.action_dimension, dtype=np.float64)
        if payload.mode == "composition":
            if payload.target_action is None:
                raise ConflictError("composition requires target_action")
            return np.clip(np.asarray(payload.target_action, dtype=np.float64), -1.0, 1.0)

        action = rng.normal(0.0, 0.30, size=self.settings.action_dimension)
        if atlas_bias is not None:
            action = 0.68 * atlas_bias + 0.32 * action
        return np.clip(action, -0.78, 0.78)

    @staticmethod
    def _remember_branch(state: SessionState, branch_node_id: str) -> None:
        state.history = [item for item in state.history if item != branch_node_id]
        state.history.append(branch_node_id)

    @staticmethod
    def _candidate_design_id(world_id: str, candidate_id: str) -> str:
        digest = hashlib.sha256(f"{world_id}:{candidate_id}".encode("utf-8")).hexdigest()
        return f"design_{digest[:32]}"

    def _design_from_artifact(
        self,
        *,
        design_id: str,
        world_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
        artifact: Any,
        parent_design_id: str | None = None,
        source_candidate_id: str | None = None,
    ) -> DesignState:
        return DesignState(
            design_id=design_id,
            world_id=world_id,
            parent_design_id=parent_design_id,
            source_candidate_id=source_candidate_id,
            seed=seed,
            prompt=prompt,
            action=np.asarray(action, dtype=np.float64).astype(float).tolist(),
            image_url=f"/assets/{design_id}.png",
            image_path=str(artifact.path),
            image_digest=artifact.digest,
            feature_vector=artifact.feature_vector,
            feature_revision=self.renderer.feature_revision,
            renderer_revision=self.renderer.revision,
            control_basis_revision=self.renderer.control_basis_revision,
        )

    def _repair_loaded_state(self, state: SessionState) -> bool:
        changed = False
        if state.world.world_id not in state.worlds:
            state.worlds[state.world.world_id] = state.world.model_copy(deep=True)
            changed = True
        for design in state.designs.values():
            if design.world_id not in state.worlds:
                state.worlds[design.world_id] = self._world_from_design(state, design)
                changed = True
        current = state.designs.get(state.current_design_id)
        if current is not None and state.world.world_id != current.world_id:
            state.world = state.worlds[current.world_id].model_copy(deep=True)
            state.prompt = state.world.prompt
            changed = True
        unique_history: list[str] = []
        for branch_id in state.history:
            if branch_id in state.branches and branch_id not in unique_history:
                unique_history.append(branch_id)
        if unique_history != state.history:
            state.history = unique_history
            changed = True
        return changed

    def _world_from_design(self, state: SessionState, design: DesignState) -> WorldState:
        world_designs = [item for item in state.designs.values() if item.world_id == design.world_id]
        roots = [item for item in world_designs if item.parent_design_id is None]
        root = min(roots or world_designs or [design], key=lambda item: item.created_at)
        return WorldState(
            world_id=design.world_id,
            seed=root.seed,
            prompt=root.prompt,
            root_design_id=root.design_id,
            renderer_revision=root.renderer_revision,
            control_basis_revision=root.control_basis_revision,
            initialization_action=root.action,
        )
