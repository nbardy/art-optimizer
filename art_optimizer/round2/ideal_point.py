from __future__ import annotations

from typing import Iterable

import numpy as np

from .contracts import IdealPointObservation, IdealPointProjection, PredictiveReceipt
from .ideal_point_math import (
    FitPolicy,
    cursor_digest,
    fit_projection,
    positive_definite,
)
from .ideal_point_predict import PREDICTIVE_REVISION, predict_receipt


class IdealPointEngine:
    """Joint-refit eight-dimensional ideal-point shadow engine."""

    engine_id = "ideal-point-8d"
    engine_revision = "joint-map-laplace/v1"
    projection_schema_revision = "ideal-point-projection/v1"
    predictive_approximation_revision = PREDICTIVE_REVISION

    def __init__(
        self,
        dimension: int = 8,
        *,
        curvature: np.ndarray | None = None,
        policy: FitPolicy | None = None,
    ) -> None:
        if not 1 <= dimension <= 16:
            raise ValueError("dimension must be between 1 and 16")
        self.dimension = dimension
        self.policy = policy or FitPolicy()
        if self.policy.predictive_samples < 2 or (
            self.policy.predictive_samples
            & (self.policy.predictive_samples - 1)
        ):
            raise ValueError("predictive_samples must be a power of two")
        value = np.eye(dimension, dtype=np.float64) if curvature is None else curvature
        self.curvature = positive_definite(
            value,
            dimension=dimension,
            minimum_eigenvalue=self.policy.minimum_eigenvalue,
            name="utility curvature",
        )

    def initialize(self, scope_id: str) -> IdealPointProjection:
        prior_mean = np.zeros(self.dimension, dtype=np.float64)
        prior_covariance = np.eye(self.dimension, dtype=np.float64) * self.policy.prior_variance
        return IdealPointProjection(
            scope_id=scope_id,
            dimension=self.dimension,
            prior_mean=prior_mean.tolist(),
            prior_covariance=prior_covariance.tolist(),
            posterior_mean=prior_mean.tolist(),
            posterior_covariance=prior_covariance.tolist(),
            utility_curvature=self.curvature.tolist(),
            temperature=self.policy.temperature,
            observations=[],
            effective_evidence_mass=0.0,
            source_event_cursor_digest=cursor_digest(()),
            optimizer_receipt={
                "converged": True,
                "iterations": 0,
                "gradient_norm": 0.0,
                "objective": 0.0,
                "fit_policy_revision": self.policy.revision,
            },
        )

    def observe(
        self,
        projection: IdealPointProjection,
        observation: IdealPointObservation,
    ) -> IdealPointProjection:
        self._validate_projection(projection)
        if observation.scope_id != projection.scope_id:
            raise ValueError("observation representation scope does not match projection")
        if any(len(action) != self.dimension for action in observation.actions):
            raise ValueError("observation action dimension does not match engine")
        if any(item.event_id == observation.event_id for item in projection.observations):
            return projection.model_copy(deep=True)
        return self.fit(projection, [*projection.observations, observation])

    def replay(
        self,
        scope_id: str,
        observations: Iterable[IdealPointObservation],
    ) -> IdealPointProjection:
        return self.fit(self.initialize(scope_id), list(observations))

    def fit(
        self,
        projection: IdealPointProjection,
        observations: list[IdealPointObservation],
    ) -> IdealPointProjection:
        self._validate_projection(projection)
        return fit_projection(
            projection,
            observations,
            dimension=self.dimension,
            curvature=self.curvature,
            policy=self.policy,
        )

    def predict(
        self,
        projection: IdealPointProjection,
        *,
        session_id: str,
        round_id: str,
        treatment_id: str,
        alternative_ids: list[str],
        actions: list[list[float]],
    ) -> PredictiveReceipt:
        self._validate_projection(projection)
        return predict_receipt(
            projection,
            dimension=self.dimension,
            curvature=self.curvature,
            policy=self.policy,
            engine_id=self.engine_id,
            engine_revision=self.engine_revision,
            session_id=session_id,
            round_id=round_id,
            treatment_id=treatment_id,
            alternative_ids=alternative_ids,
            actions=actions,
        )

    def _validate_projection(self, projection: IdealPointProjection) -> None:
        if projection.dimension != self.dimension:
            raise ValueError("projection dimension does not match engine")
        if projection.engine_id != self.engine_id:
            raise ValueError("projection belongs to a different engine")
        if projection.engine_revision != self.engine_revision:
            raise ValueError("projection revision is incompatible")
        positive_definite(
            np.asarray(projection.utility_curvature, dtype=np.float64),
            dimension=self.dimension,
            minimum_eigenvalue=self.policy.minimum_eigenvalue,
            name="projection utility curvature",
        )
