import asyncio
from pathlib import Path

import pytest

from art_optimizer.config import Settings
from art_optimizer.domain import (
    CommitPayload,
    CreateSessionRequest,
    ExposurePayload,
    FavoritePayload,
    NewWorldPayload,
    RestorePayload,
)
from art_optimizer.service import ArtOptimizerService, ConflictError


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=96,
    )


async def wait_for_ready(
    service: ArtOptimizerService,
    session_id: str,
    timeout: float = 8.0,
) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await service.get_snapshot(session_id)
        round_state = snapshot.get("active_round")
        candidates = round_state.get("candidates", []) if round_state else []
        if len(candidates) == 4 and all(candidate["status"] == "ready" for candidate in candidates):
            return snapshot
        await asyncio.sleep(0.05)
    raise AssertionError("candidate round did not become ready")


async def exercise_service(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = ArtOptimizerService(settings)
    restarted: ArtOptimizerService | None = None
    try:
        initial = await service.create_session(
            CreateSessionRequest(prompt="test garden", seed=1234)
        )
        session_id = initial["session_id"]
        initial_mutation_version = initial["mutation_version"]

        stream = service.stream(session_id)
        first_event = await anext(stream)
        assert first_event.startswith("id:")
        assert "event: session.snapshot" in first_event
        await stream.aclose()

        ready = await wait_for_ready(service, session_id)
        assert ready["version"] > initial["version"]
        assert ready["mutation_version"] == initial_mutation_version
        candidates = ready["active_round"]["candidates"]
        current_before = ready["current_design"]["design_id"]
        old_world_id = ready["world"]["world_id"]
        selected = candidates[0]
        exposed = [candidate["candidate_id"] for candidate in candidates]

        commit_payload = CommitPayload(
            request_id="command_commit_test_0001",
            exposed_candidate_ids=exposed,
            expected_mutation_version=ready["mutation_version"],
        )
        committed = await service.commit_candidate(
            session_id,
            selected["candidate_id"],
            commit_payload,
        )
        assert committed["current_design"]["design_id"] != current_before
        assert committed["learner"]["observation_count"] == 1
        assert committed["mutation_version"] == ready["mutation_version"] + 1
        assert len(committed["history"]) == 2

        duplicate = await service.commit_candidate(
            session_id,
            selected["candidate_id"],
            commit_payload,
        )
        assert duplicate == committed

        ready_after_commit = await wait_for_ready(service, session_id)
        current_design_id = ready_after_commit["current_design"]["design_id"]
        favored = await service.favorite(
            session_id,
            current_design_id,
            FavoritePayload(request_id="command_favorite_test_0001", favorite=True),
        )
        assert current_design_id in favored["favorites"]
        assert favored["atlas"]["component_count"] >= 1

        reroll_candidates = ready_after_commit["active_round"]["candidates"]
        rerolled = await service.reroll(
            session_id,
            ExposurePayload(
                request_id="command_reroll_test_0001",
                expected_mutation_version=favored["mutation_version"],
                exposed_candidate_ids=[
                    item["candidate_id"] for item in reroll_candidates
                ],
            ),
        )
        assert rerolled["current_design"]["design_id"] == current_design_id
        assert rerolled["learner"]["observation_count"] == 2

        await wait_for_ready(service, session_id)
        new_world = await service.new_world(
            session_id,
            NewWorldPayload(
                request_id="command_new_world_test_0001",
                expected_mutation_version=rerolled["mutation_version"],
            ),
        )
        assert new_world["world"]["world_id"] != old_world_id
        assert new_world["current_design"]["design_id"] != current_design_id
        assert current_design_id in new_world["favorites"]

        old_branch = committed["history"][-1]["branch_node_id"]
        restored = await service.restore(
            session_id,
            old_branch,
            RestorePayload(
                request_id="command_restore_test_0001",
                expected_mutation_version=new_world["mutation_version"],
            ),
        )
        assert restored["current_design"]["design_id"] == current_design_id
        assert restored["world"]["world_id"] == old_world_id

        ready_after_restore = await wait_for_ready(service, session_id)
        assert all(
            service._sessions[session_id].state.designs[candidate["design_id"]].world_id
            == old_world_id
            for candidate in ready_after_restore["active_round"]["candidates"]
        )

        await service.shutdown()
        restarted = ArtOptimizerService(settings)
        persisted = await restarted.get_snapshot(session_id)
        assert persisted["current_design"]["design_id"] == current_design_id
        assert persisted["world"]["world_id"] == old_world_id
        assert current_design_id in persisted["favorites"]
        assert restarted.store.integrity_check() == "ok"

        event_kinds = [event["kind"] for event in await restarted.events(session_id)]
        assert "candidate_committed" in event_kinds
        assert "round_rerolled" in event_kinds
        assert "design_favorited" in event_kinds
        assert "history_state_restored" in event_kinds
    finally:
        await service.shutdown()
        if restarted is not None:
            await restarted.shutdown()


def test_service_end_to_end(tmp_path: Path) -> None:
    asyncio.run(exercise_service(tmp_path))


async def exercise_concurrent_commands(tmp_path: Path) -> None:
    service = ArtOptimizerService(make_settings(tmp_path))
    try:
        created = await service.create_session(
            CreateSessionRequest(prompt="concurrency", seed=99)
        )
        ready = await wait_for_ready(service, created["session_id"])
        candidates = ready["active_round"]["candidates"]
        exposed = [candidate["candidate_id"] for candidate in candidates]

        first = CommitPayload(
            request_id="command_concurrent_first",
            expected_mutation_version=ready["mutation_version"],
            exposed_candidate_ids=exposed,
        )
        second = CommitPayload(
            request_id="command_concurrent_second",
            expected_mutation_version=ready["mutation_version"],
            exposed_candidate_ids=exposed,
        )
        results = await asyncio.gather(
            service.commit_candidate(
                ready["session_id"], candidates[0]["candidate_id"], first
            ),
            service.commit_candidate(
                ready["session_id"], candidates[1]["candidate_id"], second
            ),
            return_exceptions=True,
        )
        successes = [result for result in results if isinstance(result, dict)]
        conflicts = [result for result in results if isinstance(result, ConflictError)]
        assert len(successes) == 1
        assert len(conflicts) == 1
        snapshot = await service.get_snapshot(ready["session_id"])
        assert snapshot["mutation_version"] == ready["mutation_version"] + 1
        assert len(snapshot["history"]) == 2
    finally:
        await service.shutdown()


def test_concurrent_commands_only_advance_once(tmp_path: Path) -> None:
    asyncio.run(exercise_concurrent_commands(tmp_path))


async def exercise_missing_artifact_recovery(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = ArtOptimizerService(settings)
    restarted: ArtOptimizerService | None = None
    try:
        created = await service.create_session(
            CreateSessionRequest(prompt="restart", seed=77)
        )
        ready = await wait_for_ready(service, created["session_id"])
        candidate = ready["active_round"]["candidates"][0]
        design = service._sessions[created["session_id"]].state.designs[candidate["design_id"]]
        Path(design.image_path).unlink()
        await service.shutdown()

        restarted = ArtOptimizerService(settings)
        repaired = await wait_for_ready(restarted, created["session_id"])
        repaired_candidate = repaired["active_round"]["candidates"][0]
        repaired_design = restarted._sessions[created["session_id"]].state.designs[
            repaired_candidate["design_id"]
        ]
        assert Path(repaired_design.image_path).exists()
        assert repaired_design.image_digest
    finally:
        await service.shutdown()
        if restarted is not None:
            await restarted.shutdown()


def test_restart_recovers_missing_candidate_artifact(tmp_path: Path) -> None:
    asyncio.run(exercise_missing_artifact_recovery(tmp_path))


def test_stale_mutation_version_is_rejected(tmp_path: Path) -> None:
    async def run() -> None:
        service = ArtOptimizerService(make_settings(tmp_path))
        try:
            created = await service.create_session(
                CreateSessionRequest(prompt="stale", seed=55)
            )
            ready = await wait_for_ready(service, created["session_id"])
            with pytest.raises(ConflictError):
                await service.reroll(
                    created["session_id"],
                    ExposurePayload(
                        request_id="command_stale_test_0001",
                        expected_mutation_version=ready["mutation_version"] + 1,
                        exposed_candidate_ids=[],
                    ),
                )
        finally:
            await service.shutdown()

    asyncio.run(run())
