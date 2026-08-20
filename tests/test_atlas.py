from art_optimizer.atlas import PersistentPreferenceAtlas


def vector(value: float) -> list[float]:
    return [value] * 13


def action(value: float) -> list[float]:
    return [value] * 8


def test_strong_novel_evidence_spawns_modes() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(design_id="a", feature_vector=vector(0.1), action=action(-0.5), kind="favorite")
    atlas.add_evidence(design_id="b", feature_vector=vector(0.9), action=action(0.5), kind="favorite")
    assert len(atlas.state.components) == 2


def test_single_weak_novel_event_stays_provisional() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(design_id="a", feature_vector=vector(0.15), action=action(-0.4), kind="commit")
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


def test_unfavorite_retracts_strong_evidence() -> None:
    atlas = PersistentPreferenceAtlas()
    atlas.add_evidence(design_id="a", feature_vector=vector(0.2), action=action(0.2), kind="favorite")
    assert len(atlas.state.components) == 1
    assert atlas.retract_favorite("a") is True
    assert len(atlas.state.components) == 0
