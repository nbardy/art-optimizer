from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    database_path: Path
    artifacts_dir: Path
    renderer_size: int = 640
    action_dimension: int = 8
    candidate_count: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("ART_OPTIMIZER_DATA_DIR", ".art-optimizer")).resolve()
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "art_optimizer.sqlite3",
            artifacts_dir=data_dir / "artifacts",
            renderer_size=int(os.environ.get("ART_OPTIMIZER_IMAGE_SIZE", "640")),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
