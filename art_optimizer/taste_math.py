from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize

from .taste_contracts import TasteChoiceObservation, TasteFit


def choice_probability(
    inverse_temperature: float,
    center: np.ndarray,
    observation: TasteChoiceObservation,
) -> float:
    actions = observation.action_matrix()
    logits = -0.5 * inverse_temperature * np.square(
        actions - center[None, :]
    ).sum(axis=1)
    logits -= float(logits.max())
    probabilities = np.exp(logits)
    probabilities /= probabilities.sum()
    return float(np.clip(probabilities[observation.winner_index], 1e-12, 1.0))


def transition_matrix(persistence: float, prevalence: np.ndarray) -> np.ndarray:
    component_count = prevalence.size
    transition = np.broadcast_to(
        (1.0 - persistence) * prevalence[None, :],
        (component_count, component_count),
    ).copy()
    indices = np.arange(component_count)
    transition[indices, indices] += persistence
    return transition


def forward_backward(
    emissions: np.ndarray,
    prevalence: np.ndarray,
    persistence: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    observation_count, component_count = emissions.shape
    if observation_count == 0:
        return (
            np.empty((0, component_count), dtype=np.float64),
            prevalence.copy(),
            0.0,
        )
    transition = transition_matrix(persistence, prevalence)
    alpha = np.empty((observation_count, component_count), dtype=np.float64)
    scales = np.empty(observation_count, dtype=np.float64)
    prior = prevalence.copy()
    log_likelihood = 0.0
    for index in range(observation_count):
        if index > 0:
            prior = alpha[index - 1] @ transition
        unnormalized = prior * emissions[index]
        scale = float(max(unnormalized.sum(), 1e-300))
        alpha[index] = unnormalized / scale
        scales[index] = scale
        log_likelihood += math.log(scale)

    beta = np.ones((observation_count, component_count), dtype=np.float64)
    for index in range(observation_count - 2, -1, -1):
        beta[index] = transition @ (emissions[index + 1] * beta[index + 1])
        beta[index] /= max(scales[index + 1], 1e-300)
    responsibilities = alpha * beta
    responsibilities /= np.maximum(
        responsibilities.sum(axis=1, keepdims=True),
        1e-300,
    )
    return responsibilities, alpha[-1].copy(), float(log_likelihood)


def emission_matrix(
    observations: list[TasteChoiceObservation],
    centers: np.ndarray,
    inverse_temperature: float,
) -> np.ndarray:
    return np.asarray(
        [
            [
                choice_probability(inverse_temperature, center, observation)
                ** observation.observation_weight
                for center in centers
            ]
            for observation in observations
        ],
        dtype=np.float64,
    )


def predictive_evidence(
    fit: TasteFit,
    observation: TasteChoiceObservation,
    *,
    inverse_temperature: float,
    persistence: float,
) -> float:
    prior = fit.filtered_state @ transition_matrix(persistence, fit.prevalence)
    evidence = np.asarray(
        [
            choice_probability(inverse_temperature, center, observation)
            ** observation.observation_weight
            for center in fit.centers
        ],
        dtype=np.float64,
    )
    return float(np.clip(prior @ evidence, 1e-12, 1.0))


def initial_centers(
    observations: list[TasteChoiceObservation],
    component_count: int,
    dimension: int,
) -> list[np.ndarray]:
    winners = np.asarray([item.winner().action for item in observations], dtype=np.float64)
    mean = winners.mean(axis=0)
    selected = [int(np.argmax(np.linalg.norm(winners - mean[None, :], axis=1)))]
    while len(selected) < component_count:
        distances = np.linalg.norm(
            winners[:, None, :] - winners[np.asarray(selected)][None, :, :],
            axis=2,
        ).min(axis=1)
        next_index = int(np.argmax(distances))
        if next_index in selected:
            break
        selected.append(next_index)
    farthest = [winners[index] for index in selected]
    while len(farthest) < component_count:
        offset = np.zeros(dimension, dtype=np.float64)
        offset[len(farthest) % dimension] = 0.12 * (
            1 if len(farthest) % 2 == 0 else -1
        )
        farthest.append(np.clip(mean + offset, -1.0, 1.0))

    centered = winners - mean[None, :]
    if winners.shape[0] >= 2 and float(np.linalg.norm(centered)) > 1e-8:
        _, _, right = np.linalg.svd(centered, full_matrices=False)
        direction = right[0]
    else:
        direction = np.zeros(dimension, dtype=np.float64)
        direction[0] = 1.0
    line = np.clip(
        mean[None, :]
        + np.linspace(-0.45, 0.45, component_count)[:, None] * direction[None, :],
        -1.0,
        1.0,
    )
    starts = [np.asarray(farthest, dtype=np.float64), line]
    unique: list[np.ndarray] = []
    for start in starts:
        if not any(np.allclose(start, other, atol=1e-8) for other in unique):
            unique.append(start)
    return unique


def optimize_center(
    observations: list[TasteChoiceObservation],
    weights: np.ndarray,
    start: np.ndarray,
    *,
    inverse_temperature: float,
    prior_variance: float,
) -> np.ndarray:
    prior_precision = 1.0 / prior_variance

    def objective(value: np.ndarray) -> tuple[float, np.ndarray]:
        loss = 0.5 * prior_precision * float(value @ value)
        gradient = prior_precision * value.copy()
        for observation, responsibility in zip(observations, weights, strict=True):
            if responsibility <= 1e-10:
                continue
            actions = observation.action_matrix()
            logits = -0.5 * inverse_temperature * np.square(
                actions - value[None, :]
            ).sum(axis=1)
            maximum = float(logits.max())
            exp_logits = np.exp(logits - maximum)
            probabilities = exp_logits / exp_logits.sum()
            log_probability = (
                logits[observation.winner_index]
                - maximum
                - math.log(float(exp_logits.sum()))
            )
            loss -= float(responsibility) * log_probability
            expected_action = probabilities @ actions
            gradient -= float(responsibility) * inverse_temperature * (
                actions[observation.winner_index] - expected_action
            )
        return float(loss), gradient

    result = minimize(
        objective,
        np.asarray(start, dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        bounds=[(-1.25, 1.25)] * start.size,
        options={"maxiter": 120, "ftol": 1e-10, "gtol": 1e-7},
    )
    value = np.asarray(result.x, dtype=np.float64)
    if not np.isfinite(value).all():
        raise RuntimeError(f"taste center optimization failed: {result.message}")
    return value


def fit_model(
    observations: list[TasteChoiceObservation],
    component_count: int,
    *,
    dimension: int,
    inverse_temperature: float,
    persistence: float,
    prior_variance: float,
    em_iterations: int,
) -> TasteFit:
    prevalence = np.full(component_count, 1.0 / component_count, dtype=np.float64)
    if not observations:
        return TasteFit(
            component_count=component_count,
            centers=np.zeros((component_count, dimension), dtype=np.float64),
            prevalence=prevalence,
            responsibilities=np.empty((0, component_count), dtype=np.float64),
            filtered_state=prevalence.copy(),
            effective_counts=np.zeros(component_count, dtype=np.float64),
            log_likelihood=0.0,
            objective=0.0,
            converged=True,
            iterations=0,
        )

    best: TasteFit | None = None
    observation_weights = np.asarray(
        [item.observation_weight for item in observations],
        dtype=np.float64,
    )
    for start in initial_centers(observations, component_count, dimension):
        centers = start.copy()
        previous_objective = -np.inf
        converged = False
        iterations = 0
        for iteration in range(1, em_iterations + 1):
            emissions = emission_matrix(observations, centers, inverse_temperature)
            responsibilities, _, _ = forward_backward(
                emissions,
                prevalence,
                persistence,
            )
            next_centers = np.vstack(
                [
                    optimize_center(
                        observations,
                        responsibilities[:, index] * observation_weights,
                        centers[index],
                        inverse_temperature=inverse_temperature,
                        prior_variance=prior_variance,
                    )
                    for index in range(component_count)
                ]
            )
            next_emissions = emission_matrix(
                observations,
                next_centers,
                inverse_temperature,
            )
            next_responsibilities, filtered, log_likelihood = forward_backward(
                next_emissions,
                prevalence,
                persistence,
            )
            objective = log_likelihood - 0.5 * float(
                np.square(next_centers).sum() / prior_variance
            )
            movement = float(np.linalg.norm(next_centers - centers))
            delta = abs(objective - previous_objective)
            centers = next_centers
            responsibilities = next_responsibilities
            iterations = iteration
            if delta < 1e-7 and movement < 1e-6:
                converged = True
                break
            previous_objective = objective

        emissions = emission_matrix(observations, centers, inverse_temperature)
        responsibilities, filtered, log_likelihood = forward_backward(
            emissions,
            prevalence,
            persistence,
        )
        objective = log_likelihood - 0.5 * float(
            np.square(centers).sum() / prior_variance
        )
        fit = TasteFit(
            component_count=component_count,
            centers=centers,
            prevalence=prevalence,
            responsibilities=responsibilities,
            filtered_state=filtered,
            effective_counts=(
                responsibilities * observation_weights[:, None]
            ).sum(axis=0),
            log_likelihood=float(log_likelihood),
            objective=float(objective),
            converged=converged or component_count == 1,
            iterations=iterations,
        )
        if best is None or fit.objective > best.objective:
            best = fit
    if best is None:  # pragma: no cover
        raise RuntimeError("taste fitting produced no result")
    return best
