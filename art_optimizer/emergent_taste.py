from __future__ import annotations

import math

from .taste_contracts import (
    ContractModel,
    TasteAlternative,
    TasteChoiceObservation,
    TasteDesignRef,
    TasteEngineState,
    TasteFit,
    deterministic_observation_id,
)
from .taste_math import (
    choice_probability,
    fit_model,
    forward_backward,
    predictive_evidence,
    transition_matrix,
)
from .taste_projection import component_views, select_model

__all__ = [
    "ContractModel",
    "TasteAlternative",
    "TasteChoiceObservation",
    "TasteDesignRef",
    "TasteEngineState",
    "TasteFit",
    "EmergentTasteEngine",
    "deterministic_observation_id",
]


class EmergentTasteEngine:
    """Sticky finite mixture of ideal-point multinomial-choice models.

    The baseline uses uniform prevalence and one power-likelihood definition in
    both fitting and chronological scoring. Numerical routines live in small pure
    modules so they can be tested independently of UI and persistence code.
    """

    revision = "sticky-ideal-point-prequential/v2"

    def __init__(
        self,
        dimension: int,
        *,
        max_components: int = 3,
        inverse_temperature: float = 4.0,
        persistence: float = 0.84,
        prior_variance: float = 1.5,
        em_iterations: int = 30,
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
        if em_iterations < 1:
            raise ValueError("em_iterations must be positive")
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
            k: fit_model(
                observations,
                k,
                dimension=self.dimension,
                inverse_temperature=self.inverse_temperature,
                persistence=self.persistence,
                prior_variance=self.prior_variance,
                em_iterations=self.em_iterations,
            )
            for k in range(1, self.max_components + 1)
        }
        log_scores = {k: 0.0 for k in fits}
        prediction_counts = {k: 0 for k in fits}
        for observation in observations:
            for k in fits:
                key = f"k={k}"
                if key not in observation.prediction_receipts:
                    raise ValueError(
                        f"observation {observation.observation_id} lacks {key} receipt"
                    )
                log_scores[k] += math.log(
                    max(float(observation.prediction_receipts[key]), 1e-12)
                )
                prediction_counts[k] += 1
        selected_k, scored_models = select_model(
            observation_count=len(observations),
            fits=fits,
            log_scores=log_scores,
            prediction_counts=prediction_counts,
            structural_penalty=self.structural_penalty,
            simplicity_margin=self.simplicity_margin,
            min_effective_mass=self.min_effective_mass,
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
        self._validate_observations([*state.observations, observation])
        return {
            f"k={k}": predictive_evidence(
                fit,
                observation,
                inverse_temperature=self.inverse_temperature,
                persistence=self.persistence,
            )
            for k, fit in state.fits.items()
        }

    def public_view(self, state: TasteEngineState) -> dict[str, object]:
        selected = state.fits[state.selected_k]
        components, assignments = component_views(state.observations, selected)
        latest_assignment = assignments[-1] if assignments else 0
        score_by_k = {
            int(item["k"]): float(item["penalized_score"])
            for item in state.scored_models
        }
        return {
            "engine_revision": self.revision,
            "dimension": self.dimension,
            "observation_count": len(state.observations),
            "selected_component_count": state.selected_k,
            "latest_taste_id": (
                f"taste-{latest_assignment + 1}" if state.observations else None
            ),
            "score_advantage_over_one_taste": float(
                score_by_k[state.selected_k] - score_by_k[1]
            ),
            "models": state.scored_models,
            "components": components,
            "fixed_seed_required": True,
            "evidence_kind": "same-root embedding/action choices",
            "prevalence_policy": "uniform",
        }

    def _validate_observations(
        self,
        observations: list[TasteChoiceObservation],
    ) -> None:
        seen: set[str] = set()
        scope_id: str | None = None
        for observation in observations:
            if observation.dimension != self.dimension:
                raise ValueError("observation dimension does not match the taste engine")
            if observation.observation_id in seen:
                raise ValueError("observation IDs must be unique")
            if scope_id is None:
                scope_id = observation.representation_scope_id
            elif observation.representation_scope_id != scope_id:
                raise ValueError("one taste projection cannot mix representation scopes")
            seen.add(observation.observation_id)

    def _choice_probability(
        self,
        center,
        observation: TasteChoiceObservation,
    ) -> float:
        return choice_probability(self.inverse_temperature, center, observation)

    def _transition_matrix(self, prevalence):
        return transition_matrix(self.persistence, prevalence)

    def _forward_backward(self, emissions, prevalence):
        return forward_backward(emissions, prevalence, self.persistence)
