from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .domain import GaussianSnapshot


@dataclass(slots=True)
class UtilityPrediction:
    mean: np.ndarray
    variance: np.ndarray


class BayesianChoiceModel:
    """Bayesian linear multinomial-choice model with a Laplace posterior."""

    def __init__(
        self,
        action_dimension: int,
        snapshot: GaussianSnapshot | None = None,
        *,
        prior_variance: float = 3.0,
        temperature: float = 0.70,
        forgetting_factor: float = 0.992,
    ) -> None:
        self.action_dimension = action_dimension
        self.feature_dimension = self._feature_dimension(action_dimension)
        self.temperature = temperature
        self.forgetting_factor = forgetting_factor

        if snapshot is None:
            self.mean = np.zeros(self.feature_dimension, dtype=np.float64)
            self.covariance = np.eye(self.feature_dimension, dtype=np.float64) * prior_variance
            self.observation_count = 0
        else:
            if snapshot.dimension != action_dimension:
                raise ValueError("snapshot action dimension mismatch")
            self.mean = np.asarray(snapshot.mean, dtype=np.float64)
            self.covariance = np.asarray(snapshot.covariance, dtype=np.float64)
            self.observation_count = snapshot.observation_count

    @staticmethod
    def _feature_dimension(dimension: int) -> int:
        return dimension + dimension + (dimension * (dimension - 1)) // 2

    def features(self, actions: np.ndarray) -> np.ndarray:
        actions = np.asarray(actions, dtype=np.float64)
        if actions.ndim == 1:
            actions = actions[None, :]
        if actions.shape[1] != self.action_dimension:
            raise ValueError("action dimension mismatch")

        pieces = [actions, actions**2]
        interactions = []
        for left in range(self.action_dimension):
            for right in range(left + 1, self.action_dimension):
                interactions.append(actions[:, left] * actions[:, right])
        if interactions:
            pieces.append(np.stack(interactions, axis=1))
        return np.concatenate(pieces, axis=1)

    def predict(self, actions: np.ndarray) -> UtilityPrediction:
        phi = self.features(actions)
        mean = phi @ self.mean
        variance = np.einsum("ij,jk,ik->i", phi, self.covariance, phi)
        return UtilityPrediction(mean=mean, variance=np.maximum(variance, 1e-9))

    def sample_weights(self, rng: np.random.Generator) -> np.ndarray:
        covariance = self.covariance + np.eye(self.feature_dimension) * 1e-8
        return rng.multivariate_normal(self.mean, covariance)

    def update_choice(
        self,
        *,
        anchor_action: np.ndarray,
        candidate_actions: np.ndarray,
        chosen_candidate_index: int | None,
        exposure_mask: np.ndarray,
        weight: float,
        max_iterations: int = 8,
    ) -> None:
        candidate_actions = np.asarray(candidate_actions, dtype=np.float64)
        exposure_mask = np.asarray(exposure_mask, dtype=bool)
        if candidate_actions.ndim != 2 or candidate_actions.shape[1] != self.action_dimension:
            raise ValueError("candidate actions have invalid shape")
        if exposure_mask.shape != (candidate_actions.shape[0],):
            raise ValueError("exposure mask has invalid shape")

        exposed_indices = np.flatnonzero(exposure_mask)
        if exposed_indices.size == 0:
            return
        if chosen_candidate_index is not None and chosen_candidate_index not in exposed_indices:
            exposed_indices = np.unique(np.append(exposed_indices, chosen_candidate_index))

        alternatives = np.vstack([anchor_action, candidate_actions[exposed_indices]])
        x = self.features(alternatives)
        chosen = 0
        if chosen_candidate_index is not None:
            match = np.flatnonzero(exposed_indices == chosen_candidate_index)
            if match.size != 1:
                raise ValueError("chosen candidate missing from exposed alternatives")
            chosen = 1 + int(match[0])

        covariance_prior = self.covariance / self.forgetting_factor
        precision_prior = np.linalg.inv(covariance_prior + np.eye(self.feature_dimension) * 1e-9)
        prior_mean = self.mean.copy()
        w = prior_mean.copy()
        tau = self.temperature

        for _ in range(max_iterations):
            logits = (x @ w) / tau
            logits -= np.max(logits)
            probabilities = np.exp(logits)
            probabilities /= probabilities.sum()

            expected_x = probabilities @ x
            gradient = -precision_prior @ (w - prior_mean)
            gradient += (weight / tau) * (x[chosen] - expected_x)

            centered = x - expected_x
            fisher = (centered.T * probabilities) @ centered
            posterior_precision = precision_prior + (weight / (tau**2)) * fisher
            posterior_precision += np.eye(self.feature_dimension) * 1e-7

            step = np.linalg.solve(posterior_precision, gradient)
            w_next = w + step
            if np.linalg.norm(step) < 1e-7:
                w = w_next
                break
            w = w_next

        logits = (x @ w) / tau
        logits -= np.max(logits)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum()
        expected_x = probabilities @ x
        centered = x - expected_x
        fisher = (centered.T * probabilities) @ centered
        posterior_precision = precision_prior + (weight / (tau**2)) * fisher
        posterior_precision += np.eye(self.feature_dimension) * 1e-6

        self.mean = w
        self.covariance = np.linalg.inv(posterior_precision)
        self.covariance = (self.covariance + self.covariance.T) * 0.5
        self.observation_count += 1

    def snapshot(self) -> GaussianSnapshot:
        return GaussianSnapshot(
            mean=self.mean.tolist(),
            covariance=self.covariance.tolist(),
            dimension=self.action_dimension,
            feature_dimension=self.feature_dimension,
            observation_count=self.observation_count,
        )
