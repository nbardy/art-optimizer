from __future__ import annotations

import time
from pathlib import Path

import numpy as np
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


def wait_for_ready(client: TestClient, session_id: str, timeout: float = 10.0) -> dict:
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


def create_taste(client: TestClient) -> dict:
    created = client.post(
        "/api/emergent-tastes/sessions",
        json={
            "prompt": "a gallery taste study",
            "seed": 2468,
        },
    ).json()
    ready = wait_for_ready(client, created["session_id"])
    candidates = ready["active_round"]["candidates"]
    chosen = candidates[0]
    response = client.post(
        (
            f"/api/emergent-tastes/sessions/{created['session_id']}/candidates/"
            f"{chosen['candidate_id']}/commit"
        ),
        json={
            "request_id": "command_gallery_seed_vote",
            "expected_mutation_version": ready["mutation_version"],
            "exposed_candidate_ids": [item["candidate_id"] for item in candidates],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_taste_gallery_is_seed_by_strength_and_never_adds_votes(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        snapshot = create_taste(client)
        session_id = snapshot["session_id"]
        component = snapshot["emergent_tastes"]["components"][0]
        before_events = client.get(f"/api/sessions/{session_id}/event-log").json()
        before_choice_count = sum(
            item["kind"] == "emergent_taste_choice_recorded"
            for item in before_events
        )

        response = client.post(
            (
                f"/api/emergent-tastes/sessions/{session_id}/tastes/"
                f"{component['taste_id']}/gallery"
            ),
            json={
                "request_id": "command_gallery_generate_0001",
                "expected_mutation_version": snapshot["mutation_version"],
                "row_count": 2,
                "strengths": [0.5, 1.0],
                "seed_nonce": 3,
            },
        )
        assert response.status_code == 200
        gallery = response.json()
        assert gallery["row_count"] == 2
        assert gallery["strengths"] == [0.5, 1.0]
        assert len(gallery["seeds"]) == 2
        assert len(set(gallery["seeds"])) == 2
        assert len(gallery["cells"]) == 4
        assert gallery["axis"]["vertical"] == "seed"
        assert gallery["axis"]["horizontal"] == "taste strength"
        assert gallery["preference_effect"] == "none"

        center = np.asarray(component["center"])
        for cell in gallery["cells"]:
            expected = np.clip(center * cell["strength"], -1.0, 1.0)
            np.testing.assert_allclose(cell["action"], expected, atol=1e-8)
            assert client.get(cell["image_url"]).status_code == 200

        loaded = client.get(
            f"/api/emergent-tastes/sessions/{session_id}/galleries/{gallery['gallery_id']}"
        )
        assert loaded.status_code == 200
        assert loaded.json() == gallery

        after_events = client.get(f"/api/sessions/{session_id}/event-log").json()
        after_choice_count = sum(
            item["kind"] == "emergent_taste_choice_recorded"
            for item in after_events
        )
        assert after_choice_count == before_choice_count
        assert any(
            item["kind"] == "emergent_taste_gallery_generated"
            for item in after_events
        )


def test_gallery_cell_starts_fresh_fixed_root_session(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        source = create_taste(client)
        source_session_id = source["session_id"]
        taste_id = source["emergent_tastes"]["components"][0]["taste_id"]
        gallery = client.post(
            (
                f"/api/emergent-tastes/sessions/{source_session_id}/tastes/"
                f"{taste_id}/gallery"
            ),
            json={
                "request_id": "command_gallery_generate_0002",
                "expected_mutation_version": source["mutation_version"],
                "row_count": 2,
                "strengths": [0.5, 1.0],
            },
        ).json()
        cell = next(
            item
            for item in gallery["cells"]
            if item["row"] == 1 and item["column"] == 1
        )

        payload = {
            "request_id": "command_gallery_activate_0001",
            "expected_mutation_version": source["mutation_version"],
        }
        response = client.post(
            (
                f"/api/emergent-tastes/sessions/{source_session_id}/galleries/"
                f"{gallery['gallery_id']}/cells/{cell['cell_id']}/activate"
            ),
            json=payload,
        )
        assert response.status_code == 200
        created = response.json()
        assert created["session_id"] != source_session_id
        assert created["world"]["seed"] == cell["seed"]
        np.testing.assert_allclose(created["current_design"]["action"], cell["action"])
        assert created["emergent_tastes"]["observation_count"] == 0
        assert created["gallery_origin"]["preference_effect"] == "none"

        duplicate = client.post(
            (
                f"/api/emergent-tastes/sessions/{source_session_id}/galleries/"
                f"{gallery['gallery_id']}/cells/{cell['cell_id']}/activate"
            ),
            json=payload,
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["session_id"] == created["session_id"]

        source_events = client.get(
            f"/api/sessions/{source_session_id}/event-log"
        ).json()
        assert sum(
            item["kind"] == "emergent_taste_gallery_cell_activated"
            for item in source_events
        ) == 1
