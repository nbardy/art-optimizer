from pathlib import Path

from fastapi.testclient import TestClient

from art_optimizer.app import create_app
from art_optimizer.config import Settings


def test_health_and_index(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=64,
    )
    client = TestClient(create_app(settings))
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["renderer"] == "procedural-field/v1"
    index = client.get("/")
    assert index.status_code == 200
    assert "Art Optimizer" in index.text
