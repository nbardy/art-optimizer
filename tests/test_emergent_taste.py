from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from art_optimizer.emergent_taste import (
    EmergentTasteEngine,
    TasteAlternative,
    TasteChoiceObservation,
    TasteDesignRef,
    deterministic_observation_id,
)


def make_observation(index: int, winner_index: int) -> TasteChoiceObservation:
    anchor = np.zeros(2)
    left = np.asarray([-0.85, 0.0])
    right = np.asarray([0.85, 0.0])
    upper = np.asarray([0.0, 0.70])
    return TasteChoiceObservation(
        observation_id=f"observation-{index}",
        request_id=f"request-{index}",
        round_id=f"round-{index}",
        seed=42,
        control_basis_revision="test-fixed-root-2d/v1",
        anchor=TasteDesignRef(
            design_id=f"anchor-{index}",
            action=anchor.tolist(),
            image_url=f"/anchor-{index}.png",
        ),
        alternatives=[
            TasteAlternative(
                candidate_id=f"candidate-{index}-{slot}",
                design_id=f"design-{index}-{slot}",
                action=action.tolist(),
                image_url=f"/design-{index}-{slot}.png",
                slot=slot,
            )
            for slot, action in enumerate((left, right, upper), start=1)
        ],
        winner_index=winner_index,
        result_branch_node_id=f"branch-{index}",
        created_at=datetime.now(UTC).isoformat(),
    )


def record_sequence(
    engine: EmergentTasteEngine,
    winners: list[int],
) -> list[TasteChoiceObservation]:
    observations: list[TasteChoiceObservation] = []
    state = engine.fit_state(observations)
    for index, winner_index in enumerate(winners):
        observation = make_observation(index, winner_index)
        observation = observation.model_copy(
            update={
                "prediction_receipts": engine.predictive_receipts(state, observation)
            }
        )
        observations.append(observation)
        state = engine.fit_state(observations)
    return observations


def test_one_consistent_preference_stays_one_taste() -> None:
    engine = EmergentTasteEngine(2, max_components=2, em_iterations=7)
    observations = record_sequence(engine, [1] * 10)

    view = engine.replay(observations)

    assert view["selected_component_count"] == 1
    assert view["observation_count"] == 10
    assert len(view["components"]) == 1
    assert view["components"][0]["vote_count"] == 10


def test_sticky_conflicting_blocks_promote_two_predictive_tastes() -> None:
    engine = EmergentTasteEngine(
        2,
        max_components=2,
        em_iterations=8,
        structural_penalty=0.45,
    )
    winners = [1] * 4 + [2] * 4 + [1] * 4 + [2] * 4
    observations = record_sequence(engine, winners)

    first = engine.replay(observations)
    second = engine.replay(observations)

    assert first == second, "event replay must be deterministic"
    assert first["selected_component_count"] == 2
    assert first["score_advantage_over_one_taste"] > 1.0
    assert [item["vote_count"] for item in first["components"]] == [8, 8]
    centers = np.asarray([item["center"] for item in first["components"]])
    assert centers[:, 0].min() < -0.5
    assert centers[:, 0].max() > 0.5


def test_observation_ids_are_command_idempotent() -> None:
    first = deterministic_observation_id("session-one", "command-one")
    second = deterministic_observation_id("session-one", "command-one")
    other = deterministic_observation_id("session-one", "command-two")

    assert first == second
    assert first != other
