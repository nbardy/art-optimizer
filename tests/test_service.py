import asyncio
from pathlib import Path

from art_optimizer.config import Settings
from art_optimizer.domain import CommitPayload, CreateSessionRequest, ExposurePayload, FavoritePayload
from art_optimizer.service import ArtOptimizerService


async def wait_for_ready(service: ArtOptimizerService, session_id: str, timeout: float = 8.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await service.get_snapshot(session_id)
        candidates = snapshot.get("active_round", {}).get("candidates", []) if snapshot.get("active_round") else []
        if len(candidates) == 4 and all(candidate["status"] == "ready" for candidate in candidates):
            return snapshot
        await asyncio.sleep(0.05)
    raise AssertionError("candidate round did not become ready")


async def exercise_service(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=96,
    )
    service = ArtOptimizerService(settings)
    snapshot = await service.create_session(CreateSessionRequest(prompt="test garden", seed=1234))
    session_id = snapshot["session_id"]

    stream = service.stream(session_id)
    first_event = await anext(stream)
    assert first_event.startswith("event: session.snapshot")
    await stream.aclose()

    ready = await wait_for_ready(service, session_id)
    candidates = ready["active_round"]["candidates"]
    current_before = ready["current_design"]["design_id"]
    selected = candidates[0]
    exposed = [candidate["candidate_id"] for candidate in candidates]

    committed = await service.commit_candidate(
        session_id,
        selected["candidate_id"],
        CommitPayload(exposed_candidate_ids=exposed, expected_version=ready["version"]),
    )
    assert committed["current_design"]["design_id"] != current_before
    assert committed["learner"]["observation_count"] == 1
    assert len(committed["history"]) == 2

    ready_after_commit = await wait_for_ready(service, session_id)
    current_design_id = ready_after_commit["current_design"]["design_id"]
    favored = await service.favorite(
        session_id,
        current_design_id,
        FavoritePayload(favorite=True),
    )
    assert current_design_id in favored["favorites"]
    assert favored["atlas"]["component_count"] >= 1

    reroll_candidates = ready_after_commit["active_round"]["candidates"]
    rerolled = await service.reroll(
        session_id,
        ExposurePayload(exposed_candidate_ids=[item["candidate_id"] for item in reroll_candidates]),
    )
    assert rerolled["current_design"]["design_id"] == current_design_id
    assert rerolled["learner"]["observation_count"] == 2

    await wait_for_ready(service, session_id)
    new_world = await service.new_world(session_id)
    assert new_world["current_design"]["design_id"] != current_design_id
    assert current_design_id in new_world["favorites"]

    old_branch = committed["history"][-1]["branch_node_id"]
    restored = await service.restore(session_id, old_branch)
    assert restored["current_design"]["design_id"] == current_design_id

    restarted = ArtOptimizerService(settings)
    persisted = await restarted.get_snapshot(session_id)
    assert persisted["current_design"]["design_id"] == current_design_id
    assert current_design_id in persisted["favorites"]

    event_kinds = [event["kind"] for event in await service.events(session_id)]
    assert "candidate_committed" in event_kinds
    assert "round_rerolled" in event_kinds
    assert "design_favorited" in event_kinds
    assert "history_state_restored" in event_kinds


def test_service_end_to_end(tmp_path: Path) -> None:
    asyncio.run(exercise_service(tmp_path))
