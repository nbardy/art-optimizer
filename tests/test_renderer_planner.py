from pathlib import Path

import numpy as np
import pytest

from art_optimizer.domain import SearchState
from art_optimizer.planner import CandidatePlanner, PlannerContext
from art_optimizer.preference import BayesianChoiceModel
from art_optimizer.renderer import ProceduralRenderer


def test_renderer_is_deterministic_and_cache_consistent(tmp_path: Path) -> None:
    renderer = ProceduralRenderer(tmp_path, size=96)
    action = np.linspace(-0.6, 0.6, 8)
    first = renderer.render(design_id="one", seed=42, prompt="garden", action=action)
    cached = renderer.render(design_id="one", seed=42, prompt="garden", action=action)
    independent = renderer.render(design_id="two", seed=42, prompt="garden", action=action)

    assert first.path.read_bytes() == cached.path.read_bytes() == independent.path.read_bytes()
    assert first.digest == cached.digest == independent.digest
    np.testing.assert_allclose(first.feature_vector, cached.feature_vector, atol=1e-7)
    np.testing.assert_allclose(first.feature_vector, independent.feature_vector, atol=1e-7)
    assert len(first.feature_vector) == 13
    assert list(tmp_path.glob("*.tmp")) == []


def test_renderer_rejects_unsafe_or_invalid_inputs(tmp_path: Path) -> None:
    renderer = ProceduralRenderer(tmp_path, size=64)
    with pytest.raises(ValueError):
        renderer.render(
            design_id="../escape",
            seed=1,
            prompt="garden",
            action=np.zeros(8),
        )
    with pytest.raises(ValueError):
        renderer.render(
            design_id="safe",
            seed=1,
            prompt="garden",
            action=np.full(8, np.nan),
        )


def test_planner_returns_four_distinct_roles_and_actions() -> None:
    planner = CandidatePlanner(action_dimension=8, pool_size=256)
    model = BayesianChoiceModel(action_dimension=8)
    context = PlannerContext(
        anchor_action=np.zeros(8),
        search_state=SearchState(),
        atlas_bias_action=np.full(8, 0.4),
        alternate_atlas_action=np.full(8, -0.4),
    )
    proposals = planner.propose(
        model=model,
        context=context,
        rng=np.random.default_rng(7),
    )
    repeated = planner.propose(
        model=model,
        context=context,
        rng=np.random.default_rng(7),
    )

    assert [proposal.role for proposal in proposals] == list(planner.roles)
    assert [proposal.role for proposal in repeated] == list(planner.roles)
    np.testing.assert_allclose(
        [proposal.action for proposal in proposals],
        [proposal.action for proposal in repeated],
    )
    assert len({tuple(np.round(proposal.action, 8)) for proposal in proposals}) == 4
    assert all(-1.0 <= value <= 1.0 for proposal in proposals for value in proposal.action)
    assert all(np.isfinite(proposal.expected_utility) for proposal in proposals)
    assert all(proposal.uncertainty >= 0.0 for proposal in proposals)


def test_planner_rejects_incompatible_atlas_coordinates() -> None:
    planner = CandidatePlanner(action_dimension=8, pool_size=128)
    with pytest.raises(ValueError):
        planner.propose(
            model=BayesianChoiceModel(action_dimension=8),
            context=PlannerContext(
                anchor_action=np.zeros(8),
                search_state=SearchState(),
                atlas_bias_action=np.zeros(7),
            ),
            rng=np.random.default_rng(1),
        )
