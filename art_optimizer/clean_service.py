from __future__ import annotations

from typing import Any

import numpy as np

from .domain import BranchNode, ExposurePayload, new_id
from .preference import BayesianChoiceModel
from .service import ArtOptimizerService, ConflictError


class CleanArtOptimizerService(ArtOptimizerService):
    """Small correctness layer over the stable T0 service.

    The original reroll path changed preference/search state without creating a
    recoverable checkpoint. This override keeps the existing API and planner while
    ensuring every round transition has a branch snapshot that history restore can
    reproduce exactly.
    """

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

                candidates = round_state.candidates
                exposed = set(payload.exposed_candidate_ids)
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
                        self.settings.action_dimension,
                        state.active_posterior,
                    )
                    model.update_choice(
                        anchor_action=np.asarray(
                            state.current_design().action,
                            dtype=np.float64,
                        ),
                        candidate_actions=np.asarray(
                            [candidate.action for candidate in candidates],
                            dtype=np.float64,
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
                    1.25,
                    state.search_state.radius * 1.22 + 0.025,
                )
                state.search_state.consecutive_rerolls += 1
                state.search_state.consecutive_commits = 0
                state.search_state.planner_step += 1

                previous_branch_id = state.current_branch_node_id
                checkpoint = BranchNode(
                    branch_node_id=new_id("branch"),
                    design_id=state.current_design_id,
                    parent_branch_node_id=previous_branch_id,
                    posterior=state.active_posterior.model_copy(deep=True),
                    search_state=state.search_state.model_copy(deep=True),
                )
                state.branches[checkpoint.branch_node_id] = checkpoint
                state.current_branch_node_id = checkpoint.branch_node_id
                self._remember_latest_design_checkpoint(state, checkpoint.branch_node_id)

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
                        "branch_node_id": checkpoint.branch_node_id,
                        "mutation_version": state.mutation_version,
                    },
                )

            await self._cancel_stale_tasks(runtime)
            await self._publish_snapshot(runtime)
            await self._start_round(runtime)
            result = await self._snapshot(runtime)
            self.store.save_command_result(
                session_id,
                payload.request_id,
                "reroll",
                result,
            )
            return result

    @staticmethod
    def _remember_latest_design_checkpoint(state: Any, branch_node_id: str) -> None:
        design_id = state.branches[branch_node_id].design_id
        state.history = [
            existing_id
            for existing_id in state.history
            if existing_id in state.branches
            and state.branches[existing_id].design_id != design_id
        ]
        state.history.append(branch_node_id)
