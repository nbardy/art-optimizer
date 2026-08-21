import numpy as np

from art_optimizer.atlas import PersistentPreferenceAtlas


def vector(value: float) -> list[float]:
    return [value] * 13


def action(value: float) -> list[float]:
    return [value] * 8


def test_strong_novel_evidence_spawns_modes() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="a", feature_vector=vector(0.1), action=action(-0.5), kind="favorite"
    )
    atlas.add_evidence(
        design_id="b", feature_vector=vector(0.9), action=action(0.5), kind="favorite"
    )
    assert len(atlas.state.components) == 2


def test_single_weak_novel_event_stays_provisional() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="a", feature_vector=vector(0.15), action=action(-0.4), kind="commit"
    )
    assert len(atlas.state.components) == 0
    assert len(atlas.state.provisional) == 1


def test_three_coherent_weak_events_can_promote_component() -> None:
    atlas = PersistentPreferenceAtlas()
    for index, value in enumerate((0.20, 0.22, 0.19)):
        atlas.add_evidence(
            design_id=f"design-{index}",
            feature_vector=vector(value),
            action=action(value),
            kind="commit",
        )
    assert len(atlas.state.components) == 1
    assert len(atlas.state.provisional) == 0


def test_unfavorite_retracts_strong_evidence() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="a", feature_vector=vector(0.2), action=action(0.2), kind="favorite"
    )
    assert len(atlas.state.components) == 1
    assert atlas.retract_favorite("a") is True
    assert len(atlas.state.components) == 0


def test_component_identity_survives_rebuilds() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="a", feature_vector=vector(0.20), action=action(0.15), kind="favorite"
    )
    component_id = atlas.state.components[0].component_id

    atlas.add_evidence(
        design_id="b", feature_vector=vector(0.22), action=action(0.18), kind="revisit"
    )
    assert atlas.state.components[0].component_id == component_id

    atlas.rebuild()
    assert atlas.state.components[0].component_id == component_id


def test_commit_before_favorite_is_absorbed_into_component() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="same", feature_vector=vector(0.30), action=action(0.10), kind="commit"
    )
    assert len(atlas.state.provisional) == 1

    atlas.add_evidence(
        design_id="same", feature_vector=vector(0.30), action=action(0.10), kind="favorite"
    )
    assert len(atlas.state.components) == 1
    assert atlas.state.components[0].evidence_count == 2
    assert len(atlas.state.provisional) == 0


def test_guidance_never_crosses_control_basis() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(
        design_id="a",
        feature_vector=vector(0.25),
        action=action(0.4),
        kind="favorite",
        control_basis_revision="basis-a",
    )
    rng = np.random.default_rng(5)

    incompatible = atlas.choose_guidance(
        rng,
        control_basis_revision="basis-b",
        action_dimension=8,
    )
    assert incompatible.mode == "outside_prior"
    assert incompatible.action_bias is None

    atlas.state.outside_prior_mass = 0.0
    compatible = atlas.choose_guidance(
        np.random.default_rng(5),
        control_basis_revision="basis-a",
        action_dimension=8,
    )
    assert compatible.component_id == atlas.state.components[0].component_id
    assert compatible.action_bias is not None
