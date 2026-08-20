from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.stats import qmc

from .domain import CandidateProposal, CandidateRole, SearchState, new_id
from .preference import BayesianChoiceModel


@dataclass(slots=True)
class PlannerContext:
    anchor_action: np.ndarray
    search_state: SearchState
    atlas_bias_action: np.ndarray | None = None
    alternate_atlas_action: np.ndarray | None = None


class CandidatePlanner:
    """Finite-pool, role-balanced candidate planner."""

    roles: tuple[CandidateRole, CandidateRole, CandidateRole, CandidateRole] = (
        "best_local",
        "diverse_posterior",
        "informative_probe",
        "controlled_surprise",
    )

    def __init__(self, action_dimension: int = 8, pool_size: int = 1024) -> None:
        if not 1 <= action_dimension <= 16:
            raise ValueError("action_dimension must be between 1 and 16")
        if pool_size < 64:
            raise ValueError("pool_size must be at least 64")
        self.action_dimension = action_dimension
        self.pool_size = pool_size
        self.revision = "finite-pool-four-role/v2"

    def propose(
        self,
        *,
        model: BayesianChoiceModel,
        context: PlannerContext,
        rng: np.random.Generator,
    ) -> list[CandidateProposal]:
        anchor = self._validate_action(context.anchor_action, "anchor_action")
        if model.action_dimension != self.action_dimension:
            raise ValueError("planner and preference model dimensions do not match")

        normalized_context = PlannerContext(
            anchor_action=anchor,
            search_state=context.search_state,
            atlas_bias_action=self._optional_action(context.atlas_bias_action),
            alternate_atlas_action=self._optional_action(context.alternate_atlas_action),
        )
        pool = self._build_pool(context=normalized_context, rng=rng)
        predictions = model.predict_improvement(anchor, pool)
        means = predictions.mean
        stddev = np.sqrt(predictions.variance)
        delta_phi = model.relative_features(anchor, pool)
        sampled_utility = delta_phi @ model.sample_weights(rng)

        selected: list[int] = []
        proposals: list[CandidateProposal] = []

        local_distance = np.linalg.norm(pool - anchor[None, :], axis=1)
        local_mask = local_distance <= max(context.search_state.radius * 1.15, 0.25)
        if not np.any(local_mask):
            local_mask = np.ones(pool.shape[0], dtype=bool)

        first_score = means + 0.12 * stddev - 0.12 * local_distance
        first_score[~local_mask] = -np.inf
        first = self._argmax_available(first_score, selected)
        selected.append(first)
        proposals.append(self._proposal(1, self.roles[0], pool[first], means[first], stddev[first]))

        diversity = self._distance_to_selected(pool, selected)
        second_score = sampled_utility + 0.30 * stddev + 0.55 * diversity - 0.07 * local_distance
        second = self._argmax_available(second_score, selected)
        selected.append(second)
        proposals.append(self._proposal(2, self.roles[1], pool[second], means[second], stddev[second]))

        diversity = self._distance_to_selected(pool, selected)
        third_score = stddev + 0.10 * means + 0.45 * diversity - 0.04 * local_distance
        third = self._argmax_available(third_score, selected)
        selected.append(third)
        proposals.append(self._proposal(3, self.roles[2], pool[third], means[third], stddev[third]))

        diversity = self._distance_to_selected(pool, selected)
        if normalized_context.alternate_atlas_action is not None:
            target_distance = np.linalg.norm(
                pool - normalized_context.alternate_atlas_action[None, :], axis=1
            )
            fourth_score = -0.85 * target_distance + 0.32 * stddev + 0.28 * diversity + 0.08 * means
        else:
            # A bounded surprise: farther than the local best, but still informed
            # by posterior utility and uncertainty rather than raw randomness.
            fourth_score = 0.28 * means + 0.34 * stddev + 0.48 * diversity + 0.20 * local_distance
        fourth = self._argmax_available(fourth_score, selected)
        proposals.append(self._proposal(4, self.roles[3], pool[fourth], means[fourth], stddev[fourth]))

        if len({tuple(np.round(item.action, 8)) for item in proposals}) != 4:
            raise RuntimeError("planner produced a duplicate candidate slate")
        return proposals

    def _build_pool(self, *, context: PlannerContext, rng: np.random.Generator) -> np.ndarray:
        d = self.action_dimension
        anchor = context.anchor_action
        radius = context.search_state.radius

        local_count = self.pool_size // 2
        global_count = self.pool_size // 4
        directed_count = self.pool_size - local_count - global_count

        local = anchor + rng.normal(0.0, radius / np.sqrt(d), size=(local_count, d))

        power = int(np.ceil(np.log2(max(global_count, 2))))
        sobol = qmc.Sobol(d=d, scramble=True, seed=int(rng.integers(0, 2**31 - 1)))
        global_pool = sobol.random_base2(power)[:global_count] * 2.0 - 1.0

        targets = [
            target
            for target in (context.atlas_bias_action, context.alternate_atlas_action)
            if target is not None
        ]
        if not targets:
            targets = [np.zeros(d, dtype=np.float64)]
        directed = np.empty((directed_count, d), dtype=np.float64)
        for index in range(directed_count):
            target = targets[index % len(targets)]
            mix = rng.uniform(0.35, 0.90)
            point = (1.0 - mix) * anchor + mix * target
            point += rng.normal(0.0, max(radius * 0.25, 0.06), size=d)
            directed[index] = point

        pool = np.clip(np.vstack([local, global_pool, directed]), -1.0, 1.0)
        distances = np.linalg.norm(pool - anchor[None, :], axis=1)
        pool = pool[distances > 0.045]
        pool = self._deduplicate(pool)

        attempts = 0
        while pool.shape[0] < 16 and attempts < 8:
            fallback = np.clip(anchor + rng.normal(0.0, 0.25, size=(32, d)), -1.0, 1.0)
            fallback = fallback[np.linalg.norm(fallback - anchor[None, :], axis=1) > 0.045]
            pool = self._deduplicate(np.vstack([pool, fallback]))
            attempts += 1
        if pool.shape[0] < 4:
            raise RuntimeError("unable to construct a non-degenerate candidate pool")
        return pool

    def _optional_action(self, value: np.ndarray | None) -> np.ndarray | None:
        if value is None:
            return None
        return self._validate_action(value, "atlas action")

    def _validate_action(self, value: np.ndarray, name: str) -> np.ndarray:
        action = np.asarray(value, dtype=np.float64)
        if action.shape != (self.action_dimension,):
            raise ValueError(f"{name} has the wrong dimension")
        if not np.isfinite(action).all():
            raise ValueError(f"{name} must be finite")
        return np.clip(action, -1.0, 1.0)

    @staticmethod
    def _deduplicate(pool: np.ndarray) -> np.ndarray:
        if pool.size == 0:
            return pool
        rounded = np.round(pool, decimals=10)
        _, first_indices = np.unique(rounded, axis=0, return_index=True)
        return pool[np.sort(first_indices)]

    @staticmethod
    def _distance_to_selected(pool: np.ndarray, selected: list[int]) -> np.ndarray:
        selected_points = pool[selected]
        distances = np.linalg.norm(pool[:, None, :] - selected_points[None, :, :], axis=2)
        return distances.min(axis=1)

    @staticmethod
    def _argmax_available(score: np.ndarray, selected: list[int]) -> int:
        score = np.asarray(score, dtype=np.float64).copy()
        if selected:
            score[selected] = -np.inf
        index = int(np.argmax(score))
        if not np.isfinite(score[index]):
            available = [item for item in range(score.size) if item not in selected]
            if not available:
                raise RuntimeError("candidate pool exhausted")
            return available[0]
        return index

    @staticmethod
    def _proposal(
        slot: int,
        role: CandidateRole,
        action: np.ndarray,
        expected_utility: float,
        uncertainty: float,
    ) -> CandidateProposal:
        return CandidateProposal(
            candidate_id=new_id("candidate"),
            slot=slot,
            role=cast(CandidateRole, role),
            action=action.astype(float).tolist(),
            expected_utility=float(expected_utility),
            uncertainty=float(max(uncertainty, 0.0)),
        )
