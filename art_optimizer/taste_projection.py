from __future__ import annotations

import math
from typing import Literal

import numpy as np

from .taste_contracts import TasteChoiceObservation, TasteFit


def select_model(
    *,
    observation_count: int,
    fits: dict[int, TasteFit],
    log_scores: dict[int, float],
    prediction_counts: dict[int, int],
    structural_penalty: float,
    simplicity_margin: float,
    min_effective_mass: float,
) -> tuple[int, list[dict[str, object]]]:
    scored: list[dict[str, object]] = []
    for component_count in sorted(fits):
        fit = fits[component_count]
        eligible = component_count == 1 or (
            fit.converged
            and observation_count >= 3 * component_count
            and float(fit.effective_counts.min()) >= min_effective_mass
        )
        penalty = (
            structural_penalty
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
                "converged": fit.converged,
                "iterations": fit.iterations,
                "effective_counts": fit.effective_counts.astype(float).tolist(),
            }
        )
    eligible_models = [item for item in scored if item["eligible"]]
    best_score = max(float(item["penalized_score"]) for item in eligible_models)
    selected = min(
        int(item["k"])
        for item in eligible_models
        if float(item["penalized_score"]) >= best_score - simplicity_margin
    )
    for item in scored:
        item["selected"] = int(item["k"]) == selected
    return selected, scored


def component_views(
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
                "mixture_weight": float(fit.prevalence[model_index]),
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
