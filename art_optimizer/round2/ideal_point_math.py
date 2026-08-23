from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy.special import logsumexp

from ..domain import utc_now
from .contracts import IdealPointObservation, IdealPointProjection


@dataclass(frozen=True, slots=True)
class FitPolicy:
    prior_variance: float = 2.5
    temperature: float = 0.70
    max_iterations: int = 60
    tolerance: float = 1e-8
    minimum_eigenvalue: float = 1e-8
    predictive_samples: int = 128

    @property
    def revision(self) -> str:
        return "ideal-point-fit-policy/v1"


def positive_definite(
    value: np.ndarray,
    *,
    dimension: int,
    minimum_eigenvalue: float,
    name: str,
) -> np.ndarray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.shape != (dimension, dimension):
        raise ValueError(f"{name} has the wrong shape")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} contains non-finite values")
    symmetric = (matrix + matrix.T) * 0.5
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    if float(eigenvalues.min()) <= 0.0:
        raise ValueError(f"{name} must be positive definite")
    eigenvalues = np.clip(eigenvalues, minimum_eigenvalue, 1e8)
    stabilized = (eigenvectors * eigenvalues) @ eigenvectors.T
    return (stabilized + stabilized.T) * 0.5


def softmax(logits: np.ndarray) -> np.ndarray:
    values = np.asarray(logits, dtype=np.float64)
    values = values - np.max(values)
    probabilities = np.exp(values)
    total = probabilities.sum()
    if not np.isfinite(total) or total <= 0.0:
        raise FloatingPointError("choice probabilities are not finite")
    return probabilities / total


def cursor_digest(event_ids: Iterable[str]) -> str:
    return hashlib.sha256("\0".join(event_ids).encode("utf-8")).hexdigest()


def _prepare(
    observation: IdealPointObservation,
    curvature: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int, float]:
    actions = np.asarray(observation.actions, dtype=np.float64)
    if not np.isfinite(actions).all():
        raise ValueError("observation actions must be finite")
    linear = actions @ curvature
    constants = -0.5 * np.einsum("ij,jk,ik->i", actions, curvature, actions)
    return linear, constants, observation.chosen_index, observation.weight


def fit_projection(
    projection: IdealPointProjection,
    observations: list[IdealPointObservation],
    *,
    dimension: int,
    curvature: np.ndarray,
    policy: FitPolicy,
) -> IdealPointProjection:
    for observation in observations:
        if observation.scope_id != projection.scope_id:
            raise ValueError("mixed representation scopes are not allowed")
        if any(len(action) != dimension for action in observation.actions):
            raise ValueError("observation action dimension does not match engine")

    prior_mean = np.asarray(projection.prior_mean, dtype=np.float64)
    prior_covariance = positive_definite(
        np.asarray(projection.prior_covariance, dtype=np.float64),
        dimension=dimension,
        minimum_eigenvalue=policy.minimum_eigenvalue,
        name="prior covariance",
    )
    prior_precision = np.linalg.inv(prior_covariance)
    theta = np.asarray(projection.posterior_mean, dtype=np.float64).copy()
    if theta.shape != (dimension,) or not np.isfinite(theta).all():
        theta = prior_mean.copy()

    prepared = [_prepare(observation, curvature) for observation in observations]

    def objective(value: np.ndarray) -> float:
        delta = value - prior_mean
        result = -0.5 * float(delta @ prior_precision @ delta)
        for linear, constants, chosen, weight in prepared:
            logits = (linear @ value + constants) / policy.temperature
            result += weight * float(logits[chosen] - logsumexp(logits))
        return result

    converged = False
    gradient_norm = math.inf
    iterations = 0
    for iteration in range(1, policy.max_iterations + 1):
        gradient = -prior_precision @ (theta - prior_mean)
        posterior_precision = prior_precision.copy()
        for linear, constants, chosen, weight in prepared:
            logits = (linear @ theta + constants) / policy.temperature
            probabilities = softmax(logits)
            expected = probabilities @ linear
            gradient += (weight / policy.temperature) * (linear[chosen] - expected)
            centered = linear - expected
            posterior_precision += (
                weight / (policy.temperature**2)
            ) * ((centered.T * probabilities) @ centered)

        posterior_precision += np.eye(dimension) * policy.minimum_eigenvalue
        gradient_norm = float(np.linalg.norm(gradient))
        iterations = iteration
        if gradient_norm < policy.tolerance:
            converged = True
            break

        step = np.linalg.solve(posterior_precision, gradient)
        current_objective = objective(theta)
        scale = 1.0
        candidate = theta + step
        while scale > 1.0 / 1024.0 and objective(candidate) < current_objective:
            scale *= 0.5
            candidate = theta + scale * step
        theta = candidate
        if float(np.linalg.norm(scale * step)) < policy.tolerance:
            converged = True
            break

    posterior_precision = prior_precision.copy()
    for linear, constants, _chosen, weight in prepared:
        logits = (linear @ theta + constants) / policy.temperature
        probabilities = softmax(logits)
        expected = probabilities @ linear
        centered = linear - expected
        posterior_precision += (
            weight / (policy.temperature**2)
        ) * ((centered.T * probabilities) @ centered)
    posterior_precision += np.eye(dimension) * policy.minimum_eigenvalue
    posterior_covariance = positive_definite(
        np.linalg.inv(posterior_precision),
        dimension=dimension,
        minimum_eigenvalue=policy.minimum_eigenvalue,
        name="posterior covariance",
    )

    event_ids = tuple(observation.event_id for observation in observations)
    return IdealPointProjection(
        scope_id=projection.scope_id,
        dimension=dimension,
        prior_mean=prior_mean.tolist(),
        prior_covariance=prior_covariance.tolist(),
        posterior_mean=theta.astype(float).tolist(),
        posterior_covariance=posterior_covariance.astype(float).tolist(),
        utility_curvature=curvature.astype(float).tolist(),
        temperature=policy.temperature,
        observations=[item.model_copy(deep=True) for item in observations],
        effective_evidence_mass=float(sum(item.weight for item in observations)),
        source_event_cursor_digest=cursor_digest(event_ids),
        optimizer_receipt={
            "converged": converged,
            "iterations": iterations,
            "gradient_norm": gradient_norm,
            "objective": objective(theta),
            "fit_policy_revision": policy.revision,
        },
        updated_at=utc_now(),
    )
