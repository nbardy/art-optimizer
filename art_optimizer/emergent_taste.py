from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy.optimize import linear_sum_assignment, minimize


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TasteDesignRef(ContractModel):
    design_id: str
    action: list[float]
    image_url: str = ""
    branch_node_id: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: list[float]) -> list[float]:
        vector = np.asarray(value, dtype=np.float64)
        if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
            raise ValueError("action must be a non-empty finite vector")
        return value


class TasteAlternative(TasteDesignRef):
    candidate_id: str
    slot: int = Field(ge=1, le=4)


class TasteChoiceObservation(ContractModel):
    """One fixed-root multi-choice fact plus before-outcome predictions."""

    observation_id: str
    request_id: str
    round_id: str
    seed: int = Field(ge=0)
    control_basis_revision: str
    anchor: TasteDesignRef
    alternatives: list[TasteAlternative] = Field(min_length=1, max_length=4)
    winner_index: int = Field(ge=0, le=4)
    result_branch_node_id: str
    created_at: str
    observation_weight: float = Field(default=1.0, gt=0.0, le=1.0)
    prediction_receipts: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_slate(self) -> Self:
        dimension = len(self.anchor.action)
        if any(len(item.action) != dimension for item in self.alternatives):
            raise ValueError("every action in one observation must share a dimension")
        if self.winner_index > len(self.alternatives):
            raise ValueError("winner_index is outside the recorded choice set")
        candidate_ids = [item.candidate_id for item in self.alternatives]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate IDs must be unique")
        for key, probability in self.prediction_receipts.items():
            if not key.startswith("k=") or not 0.0 < float(probability) <= 1.0:
                raise ValueError("prediction receipts must be named probabilities in (0, 1]")
        return self

    @property
    def dimension(self) -> int:
        return len(self.anchor.action)

    def action_matrix(self) -> np.ndarray:
        return np.asarray(
            [self.anchor.action, *[item.action for item in self.alternatives]],
            dtype=np.float64,
        )

    def winner(self) -> TasteDesignRef:
        if self.winner_index == 0:
            return self.anchor
        return self.alternatives[self.winner_index - 1]


@dataclass(slots=True)
class TasteFit:
    component_count: int
    centers: np.ndarray
    weights: np.ndarray
    responsibilities: np.ndarray
    filtered_state: np.ndarray
    effective_counts: np.ndarray
    log_likelihood: float


@dataclass(slots=True)
class TasteEngineState:
    observations: list[TasteChoiceObservation]
    fits: dict[int, TasteFit]
    log_scores: dict[int, float]
    prediction_counts: dict[int, int]
    selected_k: int
    scored_models: list[dict[str, object]]


class EmergentTasteEngine:
    """Sticky finite mixture of ideal-point choice models.

    Rendering and noise policy stay outside this module. The engine consumes exact
    fixed-root action slates, predicts every vote before learning it, and promotes
    extra taste modes only when they improve chronological prediction.
    """

    revision = "sticky-ideal-point-prequential/v1"

    def __init__(
        self,
        dimension: int,
        *,
        max_components: int = 3,
        inverse_temperature: float = 4.0,
        persistence: float = 0.84,
        prior_variance: float = 1.5,
        em_iterations: int = 14,
        structural_penalty: float = 0.55,
        simplicity_margin: float = 0.35,
        min_effective_mass: float = 1.75,
    ) -> None:
        if not 1 <= dimension <= 16:
            raise ValueError("dimension must be between 1 and 16")
        if not 1 <= max_components <= 5:
            raise ValueError("max_components must be between 1 and 5")
        if inverse_temperature <= 0.0:
            raise ValueError("inverse_temperature must be positive")
        if not 0.0 <= persistence < 1.0:
            raise ValueError("persistence must lie in [0, 1)")
        if prior_variance <= 0.0:
            raise ValueError("prior_variance must be positive")
        self.dimension = dimension
        self.max_components = max_components
        self.inverse_temperature = float(inverse_temperature)
        self.persistence = float(persistence)
        self.prior_variance = float(prior_variance)
        self.em_iterations = int(em_iterations)
        self.structural_penalty = float(structural_penalty)
        self.simplicity_margin = float(simplicity_margin)
        self.min_effective_mass = float(min_effective_mass)

    def replay(self, observations: list[TasteChoiceObservation]) -> dict[str, object]:
        return self.public_view(self.fit_state(observations))

    def fit_state(self, observations: list[TasteChoiceObservation]) -> TasteEngineState:
        self._validate_observations(observations)
        fits = {
            k: self._fit(observations, k, warm_start=None)
            for k in range(1, self.max_components + 1)
        }
        log_scores = {k: 0.0 for k in fits}
        prediction_counts = {k: 0 for k in fits}
        for observation in observations:
            fallback = 1.0 / (len(observation.alternatives) + 1)
            for k in fits:
                probability = observation.prediction_receipts.get(f"k={k}", fallback)
                log_scores[k] += observation.observation_weight * math.log(
                    max(float(probability), 1e-12)
                )
                prediction_counts[k] += 1
        selected_k, scored_models = self._select_model(
            observation_count=len(observations),
            fits=fits,
            log_scores=log_scores,
            prediction_counts=prediction_counts,
        )
        return TasteEngineState(
            observations=observations,
            fits=fits,
            log_scores=log_scores,
            prediction_counts=prediction_counts,
            selected_k=selected_k,
            scored_models=scored_models,
        )

    def predictive_receipts(
        self,
        state: TasteEngineState,
        observation: TasteChoiceObservation,
    ) -> dict[str, float]:
        return {
            f"k={k}": self._predictive_probability(fit, observation)
            for k, fit in state.fits.items()
        }

    def public_view(self, state: TasteEngineState) -> dict[str, object]:
        selected = state.fits[state.selected_k]
        components, assignments = self._component_views(state.observations, selected)
        latest_assignment = assignments[-1] if assignments else 0
        one_score = next(
            item["penalized_score"] for item in state.scored_models if item["k"] == 1
        )
        selected_score = next(
            item["penalized_score"]
            for item in state.scored_models
            if item["k"] == state.selected_k
        )
        return {
            "engine_revision": self.revision,
            "dimension": self.dimension,
            "observation_count": len(state.observations),
            "selected_component_count": state.selected_k,
            "latest_taste_id": (
                f"taste-{latest_assignment + 1}" if state.observations else None
            ),
            "score_advantage_over_one_taste": float(selected_score - one_score),
            "models": state.scored_models,
            "components": components,
            "fixed_seed_required": True,
            "evidence_kind": "same-root embedding/action choices",
        }

    def _validate_observations(self, observations: list[TasteChoiceObservation]) -> None:
        seen: set[str] = set()
        basis: str | None = None
        for observation in observations:
            if observation.dimension != self.dimension:
                raise ValueError("observation dimension does not match the taste engine")
            if observation.observation_id in seen:
                raise ValueError("observation IDs must be unique")
            if basis is None:
                basis = observation.control_basis_revision
            elif observation.control_basis_revision != basis:
                raise ValueError("one taste projection cannot mix control bases")
            seen.add(observation.observation_id)

    def _prior_fit(self, component_count: int) -> TasteFit:
        return TasteFit(
            component_count=component_count,
            centers=np.zeros((component_count, self.dimension), dtype=np.float64),
            weights=np.full(component_count, 1.0 / component_count, dtype=np.float64),
            responsibilities=np.empty((0, component_count), dtype=np.float64),
            filtered_state=np.full(component_count, 1.0 / component_count, dtype=np.float64),
            effective_counts=np.zeros(component_count, dtype=np.float64),
            log_likelihood=0.0,
        )

    def _predictive_probability(
        self,
        fit: TasteFit,
        observation: TasteChoiceObservation,
    ) -> float:
        transition = self._transition_matrix(fit.weights)
        prior = fit.filtered_state @ transition
        emissions = np.asarray(
            [self._choice_probability(center, observation) for center in fit.centers],
            dtype=np.float64,
        )
        return float(np.clip(prior @ emissions, 1e-12, 1.0))

    def _fit(
        self,
        observations: list[TasteChoiceObservation],
        component_count: int,
        *,
        warm_start: TasteFit | None,
    ) -> TasteFit:
        if not observations:
            return self._prior_fit(component_count)
        starts = self._initial_centers(observations, component_count, warm_start)
        best: TasteFit | None = None
        best_objective = -np.inf
        for centers in starts:
            fit = self._run_em(observations, centers)
            objective = fit.log_likelihood - 0.5 * float(
                np.square(fit.centers).sum() / self.prior_variance
            )
            if objective > best_objective:
                best = fit
                best_objective = objective
        if best is None:  # pragma: no cover - defensive
            raise RuntimeError("taste model fitting produced no result")
        if warm_start is not None and warm_start.component_count == component_count:
            best = self._align_to_warm_start(best, warm_start)
        return best

    def _initial_centers(
        self,
        observations: list[TasteChoiceObservation],
        component_count: int,
        warm_start: TasteFit | None,
    ) -> list[np.ndarray]:
        winners = np.asarray([item.winner().action for item in observations], dtype=np.float64)
        mean = winners.mean(axis=0)
        starts: list[np.ndarray] = []
        if warm_start is not None and warm_start.component_count == component_count:
            starts.append(warm_start.centers.copy())

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
            axis = len(farthest) % self.dimension
            offset = np.zeros(self.dimension, dtype=np.float64)
            offset[axis] = 0.12 * (1 if len(farthest) % 2 == 0 else -1)
            farthest.append(np.clip(mean + offset, -1.0, 1.0))
        starts.append(np.asarray(farthest, dtype=np.float64))

        centered = winners - mean[None, :]
        if winners.shape[0] >= 2 and float(np.linalg.norm(centered)) > 1e-8:
            _, _, right = np.linalg.svd(centered, full_matrices=False)
            direction = right[0]
        else:
            direction = np.zeros(self.dimension, dtype=np.float64)
            direction[0] = 1.0
        offsets = np.linspace(-0.45, 0.45, component_count)
        starts.append(
            np.clip(
                mean[None, :] + offsets[:, None] * direction[None, :],
                -1.0,
                1.0,
            )
        )

        unique: list[np.ndarray] = []
        for start in starts:
            if not any(np.allclose(start, other, atol=1e-8) for other in unique):
                unique.append(start)
        return unique

    def _run_em(
        self,
        observations: list[TasteChoiceObservation],
        initial_centers: np.ndarray,
    ) -> TasteFit:
        centers = np.asarray(initial_centers, dtype=np.float64).copy()
        component_count = centers.shape[0]
        weights = np.full(component_count, 1.0 / component_count, dtype=np.float64)
        previous_objective = -np.inf

        for _ in range(self.em_iterations):
            emissions = self._emission_matrix(observations, centers)
            responsibilities, _, log_likelihood = self._forward_backward(
                emissions, weights
            )
            observation_weights = np.asarray(
                [item.observation_weight for item in observations],
                dtype=np.float64,
            )
            counts = (responsibilities * observation_weights[:, None]).sum(axis=0)
            weights = (counts + 0.6) / (
                observation_weights.sum() + 0.6 * component_count
            )
            next_centers = np.vstack(
                [
                    self._optimize_center(
                        observations,
                        responsibilities[:, index] * observation_weights,
                        centers[index],
                    )
                    for index in range(component_count)
                ]
            )
            objective = log_likelihood - 0.5 * float(
                np.square(next_centers).sum() / self.prior_variance
            )
            movement = float(np.linalg.norm(next_centers - centers))
            centers = next_centers
            if abs(objective - previous_objective) < 1e-7 and movement < 1e-6:
                break
            previous_objective = objective

        emissions = self._emission_matrix(observations, centers)
        responsibilities, filtered, log_likelihood = self._forward_backward(
            emissions, weights
        )
        observation_weights = np.asarray(
            [item.observation_weight for item in observations],
            dtype=np.float64,
        )
        counts = (responsibilities * observation_weights[:, None]).sum(axis=0)
        return TasteFit(
            component_count=component_count,
            centers=centers,
            weights=weights,
            responsibilities=responsibilities,
            filtered_state=filtered,
            effective_counts=counts,
            log_likelihood=log_likelihood,
        )

    def _emission_matrix(
        self,
        observations: list[TasteChoiceObservation],
        centers: np.ndarray,
    ) -> np.ndarray:
        return np.asarray(
            [
                [
                    self._choice_probability(center, observation)
                    ** observation.observation_weight
                    for center in centers
                ]
                for observation in observations
            ],
            dtype=np.float64,
        )

    def _choice_probability(
        self,
        center: np.ndarray,
        observation: TasteChoiceObservation,
    ) -> float:
        actions = observation.action_matrix()
        logits = -0.5 * self.inverse_temperature * np.square(
            actions - center[None, :]
        ).sum(axis=1)
        logits -= float(logits.max())
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum()
        return float(np.clip(probabilities[observation.winner_index], 1e-12, 1.0))

    def _transition_matrix(self, weights: np.ndarray) -> np.ndarray:
        component_count = weights.size
        transition = np.broadcast_to(
            (1.0 - self.persistence) * weights[None, :],
            (component_count, component_count),
        ).copy()
        indices = np.arange(component_count)
        transition[indices, indices] += self.persistence
        return transition

    def _forward_backward(
        self,
        emissions: np.ndarray,
        weights: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        observation_count, component_count = emissions.shape
        transition = self._transition_matrix(weights)
        alpha = np.empty((observation_count, component_count), dtype=np.float64)
        scales = np.empty(observation_count, dtype=np.float64)
        prior = weights.copy()
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

    def _optimize_center(
        self,
        observations: list[TasteChoiceObservation],
        weights: np.ndarray,
        start: np.ndarray,
    ) -> np.ndarray:
        beta = self.inverse_temperature
        prior_precision = 1.0 / self.prior_variance

        def objective(value: np.ndarray) -> tuple[float, np.ndarray]:
            loss = 0.5 * prior_precision * float(value @ value)
            gradient = prior_precision * value.copy()
            for observation, responsibility in zip(
                observations,
                weights,
                strict=True,
            ):
                if responsibility <= 1e-10:
                    continue
                actions = observation.action_matrix()
                logits = -0.5 * beta * np.square(
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
                gradient -= (
                    float(responsibility)
                    * beta
                    * (actions[observation.winner_index] - expected_action)
                )
            return float(loss), gradient

        result = minimize(
            objective,
            np.asarray(start, dtype=np.float64),
            method="L-BFGS-B",
            jac=True,
            bounds=[(-1.25, 1.25)] * self.dimension,
            options={"maxiter": 120, "ftol": 1e-10, "gtol": 1e-7},
        )
        value = np.asarray(result.x, dtype=np.float64)
        if not np.isfinite(value).all():
            raise RuntimeError("taste center optimization produced non-finite values")
        return value

    @staticmethod
    def _align_to_warm_start(fit: TasteFit, warm: TasteFit) -> TasteFit:
        cost = np.linalg.norm(
            warm.centers[:, None, :] - fit.centers[None, :, :],
            axis=2,
        )
        rows, columns = linear_sum_assignment(cost)
        order = columns[np.argsort(rows)]
        return TasteFit(
            component_count=fit.component_count,
            centers=fit.centers[order],
            weights=fit.weights[order],
            responsibilities=fit.responsibilities[:, order],
            filtered_state=fit.filtered_state[order],
            effective_counts=fit.effective_counts[order],
            log_likelihood=fit.log_likelihood,
        )

    def _select_model(
        self,
        *,
        observation_count: int,
        fits: dict[int, TasteFit],
        log_scores: dict[int, float],
        prediction_counts: dict[int, int],
    ) -> tuple[int, list[dict[str, object]]]:
        scored: list[dict[str, object]] = []
        for component_count in sorted(fits):
            fit = fits[component_count]
            eligible = component_count == 1 or (
                observation_count >= 3 * component_count
                and float(fit.effective_counts.min()) >= self.min_effective_mass
            )
            penalty = (
                self.structural_penalty
                * (component_count - 1)
                * math.log(observation_count + 1.0)
            )
            penalized = log_scores[component_count] - penalty
            scored.append(
                {
                    "k": component_count,
                    "prequential_log_score": float(log_scores[component_count]),
                    "prediction_count": prediction_counts[component_count],
                    "structural_penalty": float(penalty),
                    "penalized_score": float(penalized),
                    "eligible": eligible,
                    "effective_counts": fit.effective_counts.astype(float).tolist(),
                }
            )
        eligible_models = [item for item in scored if item["eligible"]]
        best_score = max(float(item["penalized_score"]) for item in eligible_models)
        selected = min(
            int(item["k"])
            for item in eligible_models
            if float(item["penalized_score"])
            >= best_score - self.simplicity_margin
        )
        for item in scored:
            item["selected"] = int(item["k"]) == selected
        return selected, scored

    def _component_views(
        self,
        observations: list[TasteChoiceObservation],
        fit: TasteFit,
    ) -> tuple[list[dict[str, object]], list[int]]:
        if not observations:
            return [], []
        assignments = np.argmax(fit.responsibilities, axis=1).astype(int).tolist()
        first_seen = {
            index: next(
                (
                    time_index
                    for time_index, assignment in enumerate(assignments)
                    if assignment == index
                ),
                10**9,
            )
            for index in range(fit.component_count)
        }
        order = sorted(
            range(fit.component_count),
            key=lambda index: (first_seen[index], index),
        )
        remap = {old: new for new, old in enumerate(order)}
        assignments = [remap[item] for item in assignments]
        components: list[dict[str, object]] = []
        for display_index, model_index in enumerate(order):
            assigned_indices = [
                index
                for index, assignment in enumerate(assignments)
                if assignment == display_index
            ]
            exemplars: list[dict[str, object]] = []
            seen_designs: set[str] = set()
            for observation_index in reversed(assigned_indices):
                observation = observations[observation_index]
                winner = observation.winner()
                if winner.design_id in seen_designs:
                    continue
                seen_designs.add(winner.design_id)
                exemplars.append(
                    {
                        "design_id": winner.design_id,
                        "image_url": winner.image_url,
                        "branch_node_id": observation.result_branch_node_id,
                        "observation_id": observation.observation_id,
                    }
                )
                if len(exemplars) == 3:
                    break
            exemplars.reverse()
            hard_count = len(assigned_indices)
            status: Literal["emerging", "established"] = (
                "established" if hard_count >= 3 else "emerging"
            )
            components.append(
                {
                    "taste_id": f"taste-{display_index + 1}",
                    "label": f"Taste {chr(65 + display_index)}",
                    "status": status,
                    "center": fit.centers[model_index].astype(float).tolist(),
                    "mixture_weight": float(fit.weights[model_index]),
                    "evidence_mass": float(fit.effective_counts[model_index]),
                    "vote_count": hard_count,
                    "exemplars": exemplars,
                    "latest_branch_node_id": (
                        observations[assigned_indices[-1]].result_branch_node_id
                        if assigned_indices
                        else None
                    ),
                }
            )
        return components, assignments


def deterministic_observation_id(session_id: str, request_id: str) -> str:
    digest = hashlib.sha256(f"{session_id}:{request_id}".encode()).hexdigest()
    return f"taste_observation_{digest[:24]}"
