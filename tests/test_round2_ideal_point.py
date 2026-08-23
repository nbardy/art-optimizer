from __future__ import annotations

import numpy as np

from art_optimizer.round2.contracts import IdealPointObservation
from art_optimizer.round2.ideal_point import IdealPointEngine


def observation(event_id: str, chosen_index: int) -> IdealPointObservation:
    negative = [-0.75, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    positive = [0.75, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return IdealPointObservation(
        event_id=event_id,
        scope_id="scope_test",
        alternative_ids=[f"{event_id}:negative", f"{event_id}:positive"],
        actions=[negative, positive],
        chosen_index=chosen_index,
        weight=1.0,
    )


def test_ideal_point_joint_refit_replays_exactly() -> None:
    engine = IdealPointEngine(8)
    events = [observation(f"event_{index}", 1) for index in range(12)]

    incremental = engine.initialize("scope_test")
    for event in events:
        incremental = engine.observe(incremental, event)
    replayed = engine.replay("scope_test", events)

    np.testing.assert_allclose(
        incremental.posterior_mean,
        replayed.posterior_mean,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        incremental.posterior_covariance,
        replayed.posterior_covariance,
        atol=1e-10,
    )
    assert incremental.posterior_mean[0] > 0.5
    assert (
        incremental.posterior_covariance[0][0]
        < incremental.posterior_covariance[1][1]
    )
    assert incremental.observation_count == 12
    assert incremental.effective_evidence_mass == 12.0


def test_ideal_point_predicts_before_observing_and_deduplicates_event_ids() -> None:
    engine = IdealPointEngine(8)
    projection = engine.initialize("scope_test")
    event = observation("event_once", 1)
    projection = engine.observe(projection, event)
    duplicate = engine.observe(projection, event)
    assert duplicate.observation_count == 1

    receipt = engine.predict(
        projection,
        session_id="session_test",
        round_id="round_test",
        treatment_id="treatment_test",
        alternative_ids=["negative", "positive"],
        actions=event.actions,
    )
    assert receipt.probabilities[1] > receipt.probabilities[0]
    assert np.isclose(sum(receipt.probabilities), 1.0)
    assert receipt.source_event_cursor_digest == projection.source_event_cursor_digest
    assert receipt.approximation_revision.startswith("scrambled-sobol")
