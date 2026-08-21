from __future__ import annotations

import asyncio
import secrets

import numpy as np

from .atlas import AtlasGuidance, PersistentPreferenceAtlas
from .config import Settings
from .domain import (
    BranchNode,
    NewWorldPayload,
    SearchState,
    WorldState,
    new_id,
)
from .event_store import EventStore
from .planner import CandidatePlanner
from .preference import BayesianChoiceModel
from .renderer import build_renderer
from .rendering import ImageRenderer, artifact_manifest_path
from .service import ArtOptimizerService, ConflictError, OperationError


class ConfiguredArtOptimizerService(ArtOptimizerService):
    """Process composition root plus experimental world-initialization policies.

    The ordinary interaction, learner, persistence, renderer, and planner remain
    owned by `ArtOptimizerService`. This subclass only composes dependencies and
    selects the initial absolute action for a new stochastic world.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        renderer: ImageRenderer | None = None,
        planner: CandidatePlanner | None = None,
    ) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self.store = EventStore(settings.database_path)
        self.renderer = renderer or build_renderer(
            settings.model_id,
            settings.artifacts_dir,
            settings.renderer_size,
        )
        capabilities = self.renderer.capabilities()
        if capabilities.action_dimension != settings.action_dimension:
            raise ValueError("renderer and configured action dimensions do not match")
        self.planner = planner or CandidatePlanner(capabilities.action_dimension)
        self.atlas = PersistentPreferenceAtlas(self.store.load_atlas())
        self._atlas_lock = asyncio.Lock()
        self._runtime_load_lock = asyncio.Lock()
        self._sessions = {}

    async def new_world(
        self,
        session_id: str,
        payload: NewWorldPayload,
    ) -> dict[str, object]:
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
            action = np.asarray(payload.target_action, dtype=np.float64)
            return np.clip(action, -1.0, 1.0)

        action = rng.normal(0.0, 0.30, size=self.settings.action_dimension)
        if atlas_bias is not None:
            action = 0.68 * atlas_bias + 0.32 * action
        return np.clip(action, -0.78, 0.78)
