from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from art_optimizer.app import create_app
from art_optimizer.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=64,
    )


def wait_for_ready(client: TestClient, session_id: str, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = client.get(
            f"/api/emergent-tastes/sessions/{session_id}"
        ).json()
        candidates = (snapshot.get("active_round") or {}).get("candidates", [])
        if len(candidates) == 4 and all(
            candidate["status"] == "ready" for candidate in candidates
        ):
            return snapshot
        time.sleep(0.05)
    raise AssertionError("emergent-taste candidate round did not become ready")


def test_emergent_taste_treatment_keeps_root_fixed_and_replays(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    session_id = ""
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/emergent-tastes/sessions",
            json={"prompt": "a fixed-root taste study", "seed": 2468},
        )
        assert created.status_code == 200
        snapshot = created.json()
        session_id = snapshot["session_id"]
        seed = snapshot["world"]["seed"]
        assert snapshot["treatment"]["treatment_id"] == "emergent-tastes"
        assert snapshot["emergent_tastes"]["fixed_seed_required"] is True
        assert snapshot["emergent_tastes"]["observation_count"] == 0

        ready = wait_for_ready(client, session_id)
        exposed = [
            candidate["candidate_id"]
            for candidate in ready["active_round"]["candidates"]
        ]
        explored = client.post(
            f"/api/emergent-tastes/sessions/{session_id}/explore",
            json={
                "request_id": "command_emergent_explore_0001",
                "expected_mutation_version": ready["mutation_version"],
                "exposed_candidate_ids": exposed,
            },
        )
        assert explored.status_code == 200
        explored_snapshot = explored.json()
        assert explored_snapshot["world"]["seed"] == seed
        assert explored_snapshot["emergent_tastes"]["observation_count"] == 0
        assert explored_snapshot["learner"]["observation_count"] == 0

        ready = wait_for_ready(client, session_id)
        candidates = ready["active_round"]["candidates"]
        chosen = candidates[0]
        exposed = [candidate["candidate_id"] for candidate in candidates]
        payload = {
            "request_id": "command_emergent_commit_0001",
            "expected_mutation_version": ready["mutation_version"],
            "exposed_candidate_ids": exposed,
        }
        committed = client.post(
            (
                f"/api/emergent-tastes/sessions/{session_id}/candidates/"
                f"{chosen['candidate_id']}/commit"
            ),
            json=payload,
        )
        assert committed.status_code == 200
        committed_snapshot = committed.json()
        assert committed_snapshot["world"]["seed"] == seed
        assert committed_snapshot["emergent_tastes"]["observation_count"] == 1
        assert committed_snapshot["emergent_tastes"]["selected_component_count"] == 1

        duplicate = client.post(
            (
                f"/api/emergent-tastes/sessions/{session_id}/candidates/"
                f"{chosen['candidate_id']}/commit"
            ),
            json=payload,
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["emergent_tastes"]["observation_count"] == 1

        events = client.get(f"/api/sessions/{session_id}/event-log").json()
        taste_events = [
            event
            for event in events
            if event["kind"] == "emergent_taste_choice_recorded"
        ]
        assert len(taste_events) == 1
        receipts = taste_events[0]["payload"]["prediction_receipts"]
        assert set(receipts) == {"k=1", "k=2", "k=3"}
        assert all(0.0 < probability <= 1.0 for probability in receipts.values())

    with TestClient(create_app(settings)) as restarted:
        replayed = restarted.get(
            f"/api/emergent-tastes/sessions/{session_id}"
        )
        assert replayed.status_code == 200
        assert replayed.json()["emergent_tastes"]["observation_count"] == 1
        assert replayed.json()["world"]["seed"] == 2468


def test_none_fit_is_an_anchor_vote_not_neutral_exploration(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        created = client.post(
            "/api/emergent-tastes/sessions",
            json={"prompt": "an anchor-choice test", "seed": 17},
        ).json()
        ready = wait_for_ready(client, created["session_id"])
        candidates = ready["active_round"]["candidates"]
        response = client.post(
            f"/api/emergent-tastes/sessions/{created['session_id']}/none-of-these",
            json={
                "request_id": "command_emergent_none_0001",
                "expected_mutation_version": ready["mutation_version"],
                "exposed_candidate_ids": [
                    candidate["candidate_id"] for candidate in candidates
                ],
            },
        )
        assert response.status_code == 200
        snapshot = response.json()
        assert snapshot["emergent_tastes"]["observation_count"] == 1
        assert snapshot["learner"]["observation_count"] == 1
        events = client.get(
            f"/api/sessions/{created['session_id']}/event-log"
        ).json()
        observation = next(
            event["payload"]
            for event in events
            if event["kind"] == "emergent_taste_choice_recorded"
        )
        assert observation["winner_index"] == 0
        assert observation["observation_weight"] == 0.35
