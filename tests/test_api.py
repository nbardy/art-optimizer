from pathlib import Path

from fastapi.testclient import TestClient

from art_optimizer.app import create_app
from art_optimizer.config import Settings
from art_optimizer.domain import NewWorldPayload


UI_IDS = {
    "current-image",
    "implicit-lanes",
    "concept-shelf",
    "lane-board",
    "emergent-tastes",
}


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=64,
    )


def test_health_models_ui_catalog_and_validation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ART_OPTIMIZER_UI", "emergent-tastes")
    with TestClient(create_app(make_settings(tmp_path))) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        assert health.json()["database"] == "ok"
        assert health.json()["model"] == "procedural"
        assert health.json()["renderer"] == "procedural-field/v4"
        assert health.json()["codec"] == "procedural-native/v1"
        assert health.json()["replay_level"] == "exact"
        assert health.json()["osi_open_source"] is True
        assert health.json()["content_filter_required"] is False
        assert health.json()["ui"] == "experiment-catalog"
        assert "emergent-tastes" in health.json()["treatments"]

        models = client.get("/api/models")
        assert models.status_code == 200
        model_ids = {model["model_id"] for model in models.json()}
        assert model_ids == {"procedural", "flux2-klein", "krea2-turbo"}

        experiments = client.get("/api/ui-experiments")
        assert experiments.status_code == 200
        assert {item["experiment_id"] for item in experiments.json()} == UI_IDS
        assert all(item["route"].startswith("/ui/") for item in experiments.json())
        for experiment_id in UI_IDS:
            page = client.get(f"/ui/{experiment_id}")
            assert page.status_code == 200
            assert "Art Optimizer" in page.text
        assert client.get("/ui/not-a-real-experiment").status_code == 404

        index = client.get("/")
        assert index.status_code == 200
        assert "Art Optimizer Experiments" in index.text
        assert "emergent_tastes.js" not in index.text

        invalid = client.post("/api/sessions", json={"prompt": "   "})
        assert invalid.status_code == 422


def test_custom_static_ui_requires_only_an_index(monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom-ui"
    custom.mkdir()
    (custom / "index.html").write_text("<h1>Custom Art UI</h1>", encoding="utf-8")
    monkeypatch.setenv("ART_OPTIMIZER_STATIC_DIR", str(custom))

    with TestClient(create_app(make_settings(tmp_path / "runtime"))) as client:
        assert "Custom Art UI" in client.get("/").text
        assert client.get("/healthz").json()["ui"] == "custom"
        assert client.get("/ui/implicit-lanes").status_code == 404


def test_composition_reset_uses_explicit_concept_action(tmp_path: Path) -> None:
    target = [-0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7]
    with TestClient(create_app(make_settings(tmp_path))) as client:
        created = client.post(
            "/api/sessions",
            json={"prompt": "a composable impossible garden", "seed": 27},
        ).json()
        assert created["world"]["initialization_mode"] == "taste_guided"
        assert created["world"]["initialization_action"] == created["current_design"]["action"]

        response = client.post(
            f"/api/sessions/{created['session_id']}/new-world",
            json={
                "request_id": "command_composition_reset",
                "expected_mutation_version": created["mutation_version"],
                "mode": "composition",
                "target_action": target,
            },
        )
        assert response.status_code == 200
        snapshot = response.json()
        assert snapshot["current_design"]["action"] == target
        assert snapshot["world"]["root_design_id"] == snapshot["current_design"]["design_id"]
        assert snapshot["world"]["initialization_mode"] == "composition"
        assert snapshot["world"]["initialization_action"] == target

        events = client.get(f"/api/sessions/{created['session_id']}/event-log").json()
        world_created = [event for event in events if event["kind"] == "world_created"][-1]
        assert world_created["payload"]["mode"] == "composition"
        assert world_created["payload"]["initial_action"] == target


def test_neutral_reset_uses_control_origin(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        created = client.post(
            "/api/sessions",
            json={"prompt": "a neutral reset study", "seed": 42},
        ).json()
        response = client.post(
            f"/api/sessions/{created['session_id']}/new-world",
            json={
                "request_id": "command_neutral_reset",
                "expected_mutation_version": created["mutation_version"],
                "mode": "neutral",
            },
        )
        assert response.status_code == 200
        snapshot = response.json()
        assert snapshot["world"]["initialization_mode"] == "neutral"
        assert snapshot["current_design"]["action"] == [0.0] * 8
        assert snapshot["world"]["initialization_action"] == [0.0] * 8
        assert snapshot["world"]["atlas_component_id"] is None
        assert snapshot["world"]["atlas_bias_action"] is None


def test_composition_payload_requires_a_target() -> None:
    try:
        NewWorldPayload(
            request_id="command_missing_target",
            mode="composition",
        )
    except ValueError:
        return
    raise AssertionError("composition mode accepted a missing target")


def test_composition_reset_rejects_wrong_dimension(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        created = client.post(
            "/api/sessions",
            json={"prompt": "dimension check", "seed": 19},
        ).json()
        response = client.post(
            f"/api/sessions/{created['session_id']}/new-world",
            json={
                "request_id": "command_wrong_dimension",
                "expected_mutation_version": created["mutation_version"],
                "mode": "composition",
                "target_action": [0.0, 0.0],
            },
        )
        assert response.status_code == 409
        assert "8 controls" in response.json()["detail"]


def test_unknown_session_is_not_found(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.get("/api/sessions/session_missing")
        assert response.status_code == 404
        assert response.json()["detail"] == "session not found"
