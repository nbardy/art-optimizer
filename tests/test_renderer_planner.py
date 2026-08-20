from pathlib import Path

import numpy as np

from art_optimizer.domain import SearchState
from art_optimizer.planner import CandidatePlanner, PlannerContext
from art_optimizer.preference import BayesianChoiceModel
from art_optimizer.renderer import ProceduralRenderer


def test_renderer_is_deterministic(tmp_path: Path) -> None:
    renderer = ProceduralRenderer(tmp_path, size=96)
    action = np.linspace(-0.6, 0.6, 8)
    first = renderer.render(design_id="one", seed=42, prompt="garden", action=action)
    second = renderer.render(design_id="two", seed=42, prompt="garden", action=action)
    assert first.path.read_bytes() == second.path.read_bytes()
    assert len(first.feature_vector) == 13


def test_planner_returns_four_distinct_roles_and_actions() -> None:
    planner = CandidatePlanner(action_dimension=8, pool_size=256)
    model = BayesianChoiceModel(action_dimension=8)
    proposals = planner.propose(
        model=model,
        context=PlannerContext(
            anchor_action=np.zeros(8),
            search_state=SearchState(),
            atlas_bias_action=np.full(8, 0.4),
            alternate_atlas_action=np.full(8, -0.4),
        ),
        rng=np.random.default_rng(7),
    )
    assert [proposal.role for proposal in proposals] == list(planner.roles)
    assert len({tuple(np.round(proposal.action, 6)) for proposal in proposals}) == 4
    assert all(-1.0 <= value <= 1.0 for proposal in proposals for value in proposal.action)
