import numpy as np
import pytest

from art_optimizer.preference import BayesianChoiceModel


def test_choice_model_learns_selected_direction() -> None:
    model = BayesianChoiceModel(action_dimension=2, prior_variance=2.0)
    anchor = np.array([0.0, 0.0])
    candidates = np.array(
        [
            [0.8, 0.0],
            [-0.8, 0.0],
            [0.0, 0.8],
            [0.0, -0.8],
        ]
    )
    mask = np.ones(4, dtype=bool)

    for _ in range(8):
        model.update_choice(
            anchor_action=anchor,
            candidate_actions=candidates,
            chosen_candidate_index=0,
            exposure_mask=mask,
            weight=1.0,
        )

    prediction = model.predict_improvement(anchor, candidates)
    assert prediction.mean[0] > prediction.mean[1]
    assert prediction.mean[0] > prediction.mean[2]
    assert model.observation_count == 8


def test_reroll_models_anchor_as_winner() -> None:
    model = BayesianChoiceModel(action_dimension=2, prior_variance=2.0)
    anchor = np.array([0.0, 0.0])
    candidates = np.array([[0.9, 0.0], [0.7, 0.2], [0.6, -0.2], [0.5, 0.4]])

    for _ in range(8):
        model.update_choice(
            anchor_action=anchor,
            candidate_actions=candidates,
            chosen_candidate_index=None,
            exposure_mask=np.ones(4, dtype=bool),
            weight=0.35,
        )

    candidate_improvements = model.predict_improvement(anchor, candidates).mean
    assert candidate_improvements.mean() < 0.0


def test_relative_prediction_matches_mean_difference() -> None:
    model = BayesianChoiceModel(action_dimension=3)
    model.mean = np.linspace(-0.3, 0.4, model.feature_dimension)
    anchor = np.array([0.1, -0.2, 0.3])
    candidates = np.array([[0.2, -0.1, 0.0], [-0.4, 0.3, 0.7]])

    absolute = model.predict(candidates).mean - model.predict(anchor).mean[0]
    relative = model.predict_improvement(anchor, candidates).mean
    np.testing.assert_allclose(relative, absolute)


def test_no_exposure_is_not_an_observation() -> None:
    model = BayesianChoiceModel(action_dimension=2)
    model.update_choice(
        anchor_action=np.zeros(2),
        candidate_actions=np.eye(2),
        chosen_candidate_index=None,
        exposure_mask=np.zeros(2, dtype=bool),
        weight=0.35,
    )
    assert model.observation_count == 0


def test_posterior_remains_finite_and_positive_definite() -> None:
    rng = np.random.default_rng(12)
    model = BayesianChoiceModel(action_dimension=4)
    anchor = np.zeros(4)

    for step in range(80):
        candidates = rng.uniform(-1.0, 1.0, size=(4, 4))
        chosen = step % 5
        model.update_choice(
            anchor_action=anchor,
            candidate_actions=candidates,
            chosen_candidate_index=None if chosen == 4 else chosen,
            exposure_mask=np.ones(4, dtype=bool),
            weight=0.35 if chosen == 4 else 1.0,
        )
        anchor = candidates[0] if chosen == 0 else anchor

    assert np.isfinite(model.mean).all()
    assert np.isfinite(model.covariance).all()
    assert np.linalg.eigvalsh(model.covariance).min() > 0.0


def test_snapshot_round_trip() -> None:
    model = BayesianChoiceModel(action_dimension=3)
    restored = BayesianChoiceModel(action_dimension=3, snapshot=model.snapshot())
    np.testing.assert_allclose(restored.mean, model.mean)
    np.testing.assert_allclose(restored.covariance, model.covariance)


def test_invalid_actions_are_rejected() -> None:
    model = BayesianChoiceModel(action_dimension=2)
    with pytest.raises(ValueError):
        model.predict(np.array([np.nan, 0.0]))
    with pytest.raises(ValueError):
        model.update_choice(
            anchor_action=np.zeros(2),
            candidate_actions=np.zeros((4, 2)),
            chosen_candidate_index=5,
            exposure_mask=np.ones(4, dtype=bool),
            weight=1.0,
        )
