import numpy as np

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

    prediction = model.predict(candidates)
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

    anchor_score = model.predict(anchor).mean[0]
    candidate_scores = model.predict(candidates).mean
    assert anchor_score > candidate_scores.mean()


def test_snapshot_round_trip() -> None:
    model = BayesianChoiceModel(action_dimension=3)
    restored = BayesianChoiceModel(action_dimension=3, snapshot=model.snapshot())
    np.testing.assert_allclose(restored.mean, model.mean)
    np.testing.assert_allclose(restored.covariance, model.covariance)
