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


def test_health_models_index_and_validation(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        assert health.json()["database"] == "ok"
        assert health.json()["model"] == "procedural"
        assert health.json()["renderer"] == "procedural-field/v4"
        assert health.json()["codec"] == "procedural-native/v1"
        assert health.json()["replay_level"] == "exact"

        models = client.get("/api/models")
        assert models.status_code == 200
        model_ids = {model["model_id"] for model in models.json()}
        assert model_ids == {"procedural", "flux2-klein", "krea2-turbo"}

        index = client.get("/")
        assert index.status_code == 200
        assert "Art Optimizer" in index.text

        invalid = client.post("/api/sessions", json={"prompt": "   "})
        assert invalid.status_code == 422


def test_unknown_session_is_not_found(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.get("/api/sessions/session_missing")
        assert response.status_code == 404
        assert response.json()["detail"] == "session not found"
