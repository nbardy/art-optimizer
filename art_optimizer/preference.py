from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .domain import GaussianSnapshot


@dataclass(slots=True)
class UtilityPrediction:
    mean: np.ndarray
    variance: np.ndarray


class BayesianChoiceModel:
    """Bayesian linear multinomial-choice model with a Laplace posterior.

    The current design is the explicit outside option. Updates are performed on
    feature differences relative to that anchor, which removes irrelevant common
    utility and matches the interaction contract directly.
    """

    def __init__(
        self,
        action_dimension: int,
        snapshot: GaussianSnapshot | None = None,
        *,
        prior_variance: float = 3.0,
        temperature: float = 0.70,
        forgetting_factor: float = 0.992,
    ) -> None:
        if not 1 <= action_dimension <= 16:
            raise ValueError("action_dimension must be between 1 and 16")
        if prior_variance <= 0.0:
            raise ValueError("prior_variance must be positive")
        if temperature <= 0.0:
            raise ValueError("temperature must be positive")
        if not 0.0 < forgetting_factor <= 1.0:
            raise ValueError("forgetting_factor must lie in (0, 1]")

        self.action_dimension = action_dimension
        self.feature_dimension = self._feature_dimension(action_dimension)
        self.temperature = float(temperature)
        self.forgetting_factor = float(forgetting_factor)

        if snapshot is None:
            self.mean = np.zeros(self.feature_dimension, dtype=np.float64)
            self.covariance = np.eye(self.feature_dimension, dtype=np.float64) * prior_variance
            self.observation_count = 0
        else:
            if snapshot.dimension != action_dimension:
                raise ValueError("snapshot action dimension mismatch")
            if snapshot.feature_dimension != self.feature_dimension:
                raise ValueError("snapshot feature dimension mismatch")
            self.mean = np.asarray(snapshot.mean, dtype=np.float64)
            self.covariance = self._stabilize_covariance(np.asarray(snapshot.covariance, dtype=np.float64))
            self.observation_count = snapshot.observation_count

    @staticmethod
    def _feature_dimension(dimension: int) -> int:
        return dimension + dimension + (dimension * (dimension - 1)) // 2

    def _validate_actions(self, actions: np.ndarray) -> np.ndarray:
        value = np.asarray(actions, dtype=np.float64)
        if value.ndim == 1:
            value = value[None, :]
        if value.ndim != 2 or value.shape[1] != self.action_dimension:
            raise ValueError("action dimension mismatch")
        if not np.isfinite(value).all():
            raise ValueError("actions must be finite")
        return value

    def features(self, actions: np.ndarray) -> np.ndarray:
        actions = self._validate_actions(actions)
        pieces = [actions, actions**2]
        interactions = []
        for left in range(self.action_dimension):
            for right in range(left + 1, self.action_dimension):
                interactions.append(actions[:, left] * actions[:, right])
        if interactions:
            pieces.append(np.stack(interactions, axis=1))
        return np.concatenate(pieces, axis=1)

    def relative_features(self, anchor_action: np.ndarray, actions: np.ndarray) -> np.ndarray:
        anchor = self._validate_actions(anchor_action)
        if anchor.shape[0] != 1:
            raise ValueError("anchor_action must describe exactly one action")
        return self.features(actions) - self.features(anchor)[0]

    def predict(self, actions: np.ndarray) -> UtilityPrediction:
        phi = self.features(actions)
        mean = phi @ self.mean
        variance = np.einsum("ij,jk,ik->i", phi, self.covariance, phi)
        return UtilityPrediction(mean=mean, variance=np.maximum(variance, 1e-10))

    def predict_improvement(self, anchor_action: np.ndarray, actions: np.ndarray) -> UtilityPrediction:
        delta = self.relative_features(anchor_action, actions)
        mean = delta @ self.mean
        variance = np.einsum("ij,jk,ik->i", delta, self.covariance, delta)
        return UtilityPrediction(mean=mean, variance=np.maximum(variance, 1e-10))

    def sample_weights(self, rng: np.random.Generator) -> np.ndarray:
        covariance = self._stabilize_covariance(self.covariance)
        return rng.multivariate_normal(self.mean, covariance, check_valid="raise")

    def update_choice(
        self,
        *,
        anchor_action: np.ndarray,
        candidate_actions: np.ndarray,
        chosen_candidate_index: int | None,
        exposure_mask: np.ndarray,
        weight: float,
        max_iterations: int = 12,
    ) -> None:
        if weight <= 0.0 or not np.isfinite(weight):
            raise ValueError("observation weight must be finite and positive")
        candidate_actions = self._validate_actions(candidate_actions)
        exposure_mask = np.asarray(exposure_mask, dtype=bool)
        if exposure_mask.shape != (candidate_actions.shape[0],):
            raise ValueError("exposure mask has invalid shape")
        if chosen_candidate_index is not None and not 0 <= chosen_candidate_index < candidate_actions.shape[0]:
            raise ValueError("chosen candidate index is out of range")

        exposed_indices = np.flatnonzero(exposure_mask)
        if exposed_indices.size == 0:
            return
        if chosen_candidate_index is not None and chosen_candidate_index not in exposed_indices:
            exposed_indices = np.unique(np.append(exposed_indices, chosen_candidate_index))

        relative = self.relative_features(anchor_action, candidate_actions[exposed_indices])
        # Alternative zero is the current design and therefore has zero relative utility.
        x = np.vstack([np.zeros((1, self.feature_dimension), dtype=np.float64), relative])
        chosen = 0
        if chosen_candidate_index is not None:
            match = np.flatnonzero(exposed_indices == chosen_candidate_index)
            if match.size != 1:
                raise ValueError("chosen candidate missing from exposed alternatives")
            chosen = 1 + int(match[0])

        covariance_prior = self._stabilize_covariance(self.covariance / self.forgetting_factor)
        precision_prior = np.linalg.inv(covariance_prior)
        prior_mean = self.mean.copy()
        current = prior_mean.copy()
        tau = self.temperature

        def objective(weights: np.ndarray) -> float:
            delta = weights - prior_mean
            logits = (x @ weights) / tau
            maximum = float(np.max(logits))
            log_normalizer = maximum + float(np.log(np.exp(logits - maximum).sum()))
            return float(-0.5 * delta @ precision_prior @ delta + weight * (logits[chosen] - log_normalizer))

        for _ in range(max_iterations):
            logits = (x @ current) / tau
            logits -= np.max(logits)
            probabilities = np.exp(logits)
            probabilities /= probabilities.sum()

            expected_x = probabilities @ x
            gradient = -precision_prior @ (current - prior_mean)
            gradient += (weight / tau) * (x[chosen] - expected_x)

            centered = x - expected_x
            fisher = (centered.T * probabilities) @ centered
            posterior_precision = precision_prior + (weight / (tau**2)) * fisher
            posterior_precision += np.eye(self.feature_dimension) * 1e-8
            step = np.linalg.solve(posterior_precision, gradient)

            # Damped Newton ascent prevents a single sharp observation from
            # producing an invalid or numerically explosive posterior.
            old_objective = objective(current)
            scale = 1.0
            next_value = current + step
            while scale > 1.0 / 128.0 and objective(next_value) < old_objective:
                scale *= 0.5
                next_value = current + scale * step
            current = next_value
            if np.linalg.norm(scale * step) < 1e-7:
                break

        logits = (x @ current) / tau
        logits -= np.max(logits)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum()
        expected_x = probabilities @ x
        centered = x - expected_x
        fisher = (centered.T * probabilities) @ centered
        posterior_precision = precision_prior + (weight / (tau**2)) * fisher
        posterior_precision += np.eye(self.feature_dimension) * 1e-7

        self.mean = current
        self.covariance = self._stabilize_covariance(np.linalg.inv(posterior_precision))
        self.observation_count += 1

    @staticmethod
    def _stabilize_covariance(covariance: np.ndarray) -> np.ndarray:
        covariance = np.asarray(covariance, dtype=np.float64)
        if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
            raise ValueError("covariance must be square")
        if not np.isfinite(covariance).all():
            raise ValueError("covariance contains non-finite values")
        symmetric = (covariance + covariance.T) * 0.5
        eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
        eigenvalues = np.clip(eigenvalues, 1e-9, 1e6)
        stabilized = (eigenvectors * eigenvalues) @ eigenvectors.T
        return (stabilized + stabilized.T) * 0.5

    def snapshot(self) -> GaussianSnapshot:
        return GaussianSnapshot(
            mean=self.mean.tolist(),
            covariance=self.covariance.tolist(),
            dimension=self.action_dimension,
            feature_dimension=self.feature_dimension,
            observation_count=self.observation_count,
        )
