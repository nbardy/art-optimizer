from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import numpy as np

from .atlas import PersistentPreferenceAtlas
from .config import Settings
from .domain import (
    BranchNode,
    CandidateRound,
    CommitPayload,
    CreateSessionRequest,
    DesignState,
    ExposurePayload,
    FavoritePayload,
    SearchState,
    SessionState,
    WorldState,
    new_id,
    utc_now,
)
from .event_store import EventStore
from .planner import CandidatePlanner, PlannerContext
from .preference import BayesianChoiceModel
from .renderer import ProceduralRenderer


class NotFoundError(KeyError):
    pass


class ConflictError(RuntimeError):
    pass


@dataclass(slots=True)
class SessionRuntime:
    state: SessionState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    render_tasks: set[asyncio.Task[Any]] = field(default_factory=set)


class ArtOptimizerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self.store = EventStore(settings.database_path)
        self.renderer = ProceduralRenderer(settings.artifacts_dir, settings.renderer_size)
        self.planner = CandidatePlanner(settings.action_dimension)
        self.atlas = PersistentPreferenceAtlas(self.store.load_atlas())
        self._atlas_lock = asyncio.Lock()
        self._sessions: dict[str, SessionRuntime] = {}

    async def create_session(self, request: CreateSessionRequest) -> dict[str, Any]:
        session_id = new_id("session")
        seed = request.seed if request.seed is not None else secrets.randbits(62)
        rng = np.random.default_rng(seed)

        async with self._atlas_lock:
            guidance = self.atlas.choose_guidance(rng)
            atlas_summary = self.atlas.summary()

        action = rng.normal(0.0, 0.28, size=self.settings.action_dimension)
        if guidance.action_bias is not None and guidance.action_bias.shape == action.shape:
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
        root_design = DesignState(
            design_id=root_design_id,
            world_id=world_id,
            seed=seed,
            prompt=request.prompt,
            action=action.tolist(),
            image_url=f"/assets/{root_design_id}.png",
            image_path=str(artifact.path),
            feature_vector=artifact.feature_vector,
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
            atlas_component_id=guidance.component_id,
            atlas_bias_action=guidance.action_bias.tolist() if guidance.action_bias is not None else None,
        )
        state = SessionState(
            session_id=session_id,
            prompt=request.prompt,
            world=world,
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
                "atlas_component_id": guidance.component_id,
                "atlas_mode": guidance.mode,
            },
        )
        await self._start_round(runtime)
        return self.public_snapshot(runtime.state, atlas_summary=atlas_summary)

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.lock:
            return self.public_snapshot(runtime.state)

    async def stream(self, session_id: str) -> AsyncIterator[str]:
        runtime = await self._get_runtime(session_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        runtime.subscribers.add(queue)
        await queue.put({"type": "session.snapshot", "payload": self.public_snapshot(runtime.state)})
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    data = json.dumps(event["payload"], separators=(",", ":"))
                    yield f"event: {event['type']}\ndata: {data}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            runtime.subscribers.discard(queue)

    async def commit_candidate(
        self,
        session_id: str,
        candidate_id: str,
        payload: CommitPayload,
    ) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.lock:
            state = runtime.state
            round_state = state.active_round
            if round_state is None or round_state.status in {"closed", "cancelled"}:
                raise ConflictError("there is no active round")
            if payload.expected_version is not None and payload.expected_version != state.version:
                raise ConflictError("session version is stale")

            candidates = round_state.candidates
            chosen_index = next(
                (index for index, candidate in enumerate(candidates) if candidate.candidate_id == candidate_id),
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
                [candidate.candidate_id in exposed and candidate.status == "ready" for candidate in candidates],
                dtype=bool,
            )
            model = BayesianChoiceModel(self.settings.action_dimension, state.active_posterior)
            model.update_choice(
                anchor_action=np.asarray(state.current_design().action),
                candidate_actions=np.asarray([candidate.action for candidate in candidates]),
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
            state.history.append(new_branch.branch_node_id)
            round_state.status = "closed"
            state.active_round = None
            state.status = "generating"
            state.touch()

            selected_design = state.designs[chosen.design_id]
            self.store.record_session_event(
                state,
                "candidate_committed",
                {
                    "round_id": round_state.round_id,
                    "candidate_id": candidate_id,
                    "design_id": chosen.design_id,
                    "exposed_candidate_ids": sorted(exposed),
                    "branch_node_id": new_branch.branch_node_id,
                },
            )

        await self._add_atlas_evidence(selected_design, "commit")
        await self._cancel_stale_tasks(runtime)
        await self._publish_snapshot(runtime)
        await self._start_round(runtime)
        return self.public_snapshot(runtime.state)

    async def reroll(self, session_id: str, payload: ExposurePayload) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        async with runtime.lock:
            state = runtime.state
            round_state = state.active_round
            if round_state is None or round_state.status in {"closed", "cancelled"}:
                raise ConflictError("there is no active round")

            exposed = set(payload.exposed_candidate_ids)
            candidates = round_state.candidates
            exposure_mask = np.asarray(
                [candidate.candidate_id in exposed and candidate.status == "ready" for candidate in candidates],
                dtype=bool,
            )
            exposed_count = int(exposure_mask.sum())

            if exposed_count >= 2:
                model = BayesianChoiceModel(self.settings.action_dimension, state.active_posterior)
                model.update_choice(
                    anchor_action=np.asarray(state.current_design().action),
                    candidate_actions=np.asarray([candidate.action for candidate in candidates]),
                    chosen_candidate_index=None,
                    exposure_mask=exposure_mask,
                    weight=0.35,
                )
                state.active_posterior = model.snapshot()
                event_kind = "round_rerolled"
            else:
                event_kind = "round_skipped"

            state.search_state.radius = min(1.25, state.search_state.radius * 1.22 + 0.025)
            state.search_state.consecutive_rerolls += 1
            state.search_state.consecutive_commits = 0
            state.search_state.planner_step += 1
            round_state.status = "closed"
            state.active_round = None
            state.status = "generating"
            state.touch()

            self.store.record_session_event(
                state,
                event_kind,
                {
                    "round_id": round_state.round_id,
                    "exposed_candidate_ids": sorted(exposed),
                    "exposed_count": exposed_count,
                    "radius": state.search_state.radius,
                },
            )

        await self._cancel_stale_tasks(runtime)
        await self._publish_snapshot(runtime)
        await self._start_round(runtime)
        return self.public_snapshot(runtime.state)

    async def favorite(
        self,
        session_id: str,
        design_id: str,
        payload: FavoritePayload,
    ) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        design: DesignState
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
                    {"design_id": design_id},
                )

        if changed:
            if payload.favorite:
                await self._add_atlas_evidence(design, "favorite")
            else:
                async with self._atlas_lock:
                    self.atlas.retract_favorite(design_id)
                    self.store.save_atlas(self.atlas.state)
            await self._publish_snapshot(runtime)
        return self.public_snapshot(runtime.state)

    async def new_world(self, session_id: str) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        await self._cancel_stale_tasks(runtime)

        async with runtime.lock:
            state = runtime.state
            if state.active_round is not None:
                state.active_round.status = "cancelled"
                state.active_round = None
            state.status = "generating"
            state.touch()
            self.store.save_session(state)
            prompt = state.prompt

        seed = secrets.randbits(62)
        rng = np.random.default_rng(seed)
        async with self._atlas_lock:
            guidance = self.atlas.choose_guidance(rng)

        action = rng.normal(0.0, 0.30, size=self.settings.action_dimension)
        if guidance.action_bias is not None and guidance.action_bias.shape == action.shape:
            action = 0.68 * guidance.action_bias + 0.32 * action
        action = np.clip(action, -0.78, 0.78)
        world_id = new_id("world")
        root_design_id = new_id("design")
        artifact = await asyncio.to_thread(
            self.renderer.render,
            design_id=root_design_id,
            seed=seed,
            prompt=prompt,
            action=action,
        )
        design = DesignState(
            design_id=root_design_id,
            world_id=world_id,
            seed=seed,
            prompt=prompt,
            action=action.tolist(),
            image_url=f"/assets/{root_design_id}.png",
            image_path=str(artifact.path),
            feature_vector=artifact.feature_vector,
        )
        model = BayesianChoiceModel(self.settings.action_dimension)
        search_state = SearchState()
        branch = BranchNode(
            branch_node_id=new_id("branch"),
            design_id=root_design_id,
            posterior=model.snapshot(),
            search_state=search_state.model_copy(deep=True),
        )

        async with runtime.lock:
            state = runtime.state
            state.world = WorldState(
                world_id=world_id,
                seed=seed,
                prompt=prompt,
                root_design_id=root_design_id,
                atlas_component_id=guidance.component_id,
                atlas_bias_action=guidance.action_bias.tolist() if guidance.action_bias is not None else None,
            )
            state.designs[root_design_id] = design
            state.branches[branch.branch_node_id] = branch
            state.current_design_id = root_design_id
            state.current_branch_node_id = branch.branch_node_id
            state.active_posterior = model.snapshot()
            state.search_state = search_state
            state.history.append(branch.branch_node_id)
            state.status = "generating"
            state.touch()
            self.store.record_session_event(
                state,
                "world_created",
                {
                    "world_id": world_id,
                    "root_design_id": root_design_id,
                    "seed": seed,
                    "atlas_component_id": guidance.component_id,
                    "atlas_mode": guidance.mode,
                },
            )

        await self._publish_snapshot(runtime)
        await self._start_round(runtime)
        return self.public_snapshot(runtime.state)

    async def restore(self, session_id: str, branch_node_id: str) -> dict[str, Any]:
        runtime = await self._get_runtime(session_id)
        await self._cancel_stale_tasks(runtime)
        async with runtime.lock:
            state = runtime.state
            if branch_node_id not in state.branches:
                raise NotFoundError("history checkpoint not found")
            branch = state.branches[branch_node_id]
            if state.active_round is not None:
                state.active_round.status = "cancelled"
            state.active_round = None
            state.current_branch_node_id = branch_node_id
            state.current_design_id = branch.design_id
            state.active_posterior = branch.posterior.model_copy(deep=True)
            state.search_state = branch.search_state.model_copy(deep=True)
            state.search_state.planner_step += 1
            state.history.append(branch_node_id)
            state.status = "generating"
            state.touch()
            design = state.designs[branch.design_id]
            self.store.record_session_event(
                state,
                "history_state_restored",
                {"branch_node_id": branch_node_id, "design_id": branch.design_id},
            )

        await self._add_atlas_evidence(design, "revisit")
        await self._publish_snapshot(runtime)
        await self._start_round(runtime)
        return self.public_snapshot(runtime.state)

    async def events(self, session_id: str) -> list[dict[str, Any]]:
        await self._get_runtime(session_id)
        return self.store.list_events(session_id)

    async def _start_round(self, runtime: SessionRuntime) -> None:
        async with runtime.lock:
            state = runtime.state
            anchor = state.current_design()
            model = BayesianChoiceModel(self.settings.action_dimension, state.active_posterior)
            seed_material = (
                f"{state.session_id}:{state.world.world_id}:{state.current_branch_node_id}:"
                f"{state.search_state.planner_step}:{state.version}"
            ).encode("utf-8")
            planner_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "little")
            rng = np.random.default_rng(planner_seed)

            atlas_bias = (
                np.asarray(state.world.atlas_bias_action, dtype=np.float64)
                if state.world.atlas_bias_action is not None
                else None
            )
            async with self._atlas_lock:
                alternate = self.atlas.alternate_action_bias(state.world.atlas_component_id)

            proposals = self.planner.propose(
                model=model,
                context=PlannerContext(
                    anchor_action=np.asarray(anchor.action, dtype=np.float64),
                    search_state=state.search_state,
                    atlas_bias_action=atlas_bias,
                    alternate_atlas_action=alternate,
                ),
                rng=rng,
            )
            round_state = CandidateRound(
                round_id=new_id("round"),
                parent_design_id=anchor.design_id,
                parent_branch_node_id=state.current_branch_node_id,
                branch_version=state.version,
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
        try:
            async with runtime.lock:
                state = runtime.state
                round_state = state.active_round
                if round_state is None or round_state.round_id != round_id:
                    return
                candidate = next(item for item in round_state.candidates if item.candidate_id == candidate_id)
                candidate.status = "rendering"
                parent_design_id = round_state.parent_design_id
                world = state.world.model_copy(deep=True)
                action = np.asarray(candidate.action, dtype=np.float64)
                slot = candidate.slot

            await self._publish_snapshot(runtime)
            # Stagger completion so the browser exercises true per-slot streaming.
            await asyncio.sleep(0.055 * slot)
            design_id = new_id("design")
            artifact = await asyncio.to_thread(
                self.renderer.render,
                design_id=design_id,
                seed=world.seed,
                prompt=world.prompt,
                action=action,
            )

            async with runtime.lock:
                state = runtime.state
                round_state = state.active_round
                if round_state is None or round_state.round_id != round_id:
                    return
                candidate = next(item for item in round_state.candidates if item.candidate_id == candidate_id)
                design = DesignState(
                    design_id=design_id,
                    world_id=world.world_id,
                    parent_design_id=parent_design_id,
                    source_candidate_id=candidate_id,
                    seed=world.seed,
                    prompt=world.prompt,
                    action=action.tolist(),
                    image_url=f"/assets/{design_id}.png",
                    image_path=str(artifact.path),
                    feature_vector=artifact.feature_vector,
                )
                state.designs[design_id] = design
                candidate.status = "ready"
                candidate.design_id = design_id
                candidate.image_url = design.image_url

                complete = all(item.status in {"ready", "failed"} for item in round_state.candidates)
                if complete:
                    round_state.status = "ready"
                    state.status = "ready"
                state.touch()
                self.store.record_session_event(
                    state,
                    "candidate_ready",
                    {
                        "round_id": round_id,
                        "candidate_id": candidate_id,
                        "design_id": design_id,
                        "slot": candidate.slot,
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
                candidate = next(item for item in round_state.candidates if item.candidate_id == candidate_id)
                candidate.status = "failed"
                candidate.error = str(error)
                if all(item.status in {"ready", "failed"} for item in round_state.candidates):
                    round_state.status = "ready"
                    state.status = "ready"
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
            )
            self.store.save_atlas(self.atlas.state)

    async def _get_runtime(self, session_id: str) -> SessionRuntime:
        runtime = self._sessions.get(session_id)
        if runtime is not None:
            return runtime
        state = self.store.load_session(session_id)
        if state is None:
            raise NotFoundError("session not found")
        runtime = SessionRuntime(state=state)
        self._sessions[session_id] = runtime
        round_state = state.active_round
        if round_state is not None and round_state.status == "rendering":
            for candidate in round_state.candidates:
                if candidate.status in {"queued", "rendering"}:
                    candidate.status = "queued"
                    task = asyncio.create_task(
                        self._render_candidate(runtime, round_state.round_id, candidate.candidate_id)
                    )
                    runtime.render_tasks.add(task)
                    task.add_done_callback(runtime.render_tasks.discard)
            self.store.save_session(state)
        return runtime

    async def _cancel_stale_tasks(self, runtime: SessionRuntime) -> None:
        tasks = [task for task in runtime.render_tasks if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _publish_snapshot(self, runtime: SessionRuntime) -> None:
        payload = self.public_snapshot(runtime.state)
        event = {"type": "session.snapshot", "payload": payload}
        for queue in list(runtime.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def public_snapshot(
        self,
        state: SessionState,
        *,
        atlas_summary: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        current = state.current_design()
        round_payload = state.active_round.model_dump(mode="json") if state.active_round else None
        history_items = []
        for branch_id in state.history[-10:]:
            branch = state.branches.get(branch_id)
            if branch is None:
                continue
            design = state.designs[branch.design_id]
            history_items.append(
                {
                    "branch_node_id": branch.branch_node_id,
                    "design_id": design.design_id,
                    "image_url": design.image_url,
                    "favorite": design.design_id in state.favorites,
                    "current": branch.branch_node_id == state.current_branch_node_id,
                    "created_at": branch.created_at,
                }
            )
        return {
            "session_id": state.session_id,
            "version": state.version,
            "prompt": state.prompt,
            "status": state.status,
            "world": state.world.model_dump(mode="json"),
            "current_design": current.model_dump(mode="json"),
            "current_branch_node_id": state.current_branch_node_id,
            "active_round": round_payload,
            "favorites": state.favorites,
            "history": history_items,
            "search": state.search_state.model_dump(mode="json"),
            "learner": {
                "observation_count": state.active_posterior.observation_count,
                "feature_dimension": state.active_posterior.feature_dimension,
            },
            "atlas": atlas_summary if atlas_summary is not None else self.atlas.summary(),
        }
