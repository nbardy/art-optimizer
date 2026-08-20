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
    renderer_kind: str = "procedural"

    def __post_init__(self) -> None:
        if not 64 <= self.renderer_size <= 2048:
            raise ValueError("renderer_size must be between 64 and 2048 pixels")
        if not 1 <= self.action_dimension <= 16:
            raise ValueError("action_dimension must be between 1 and 16")
        if self.candidate_count != 4:
            raise ValueError("the v0 interaction requires exactly four candidates")
        if self.renderer_kind not in {"procedural"}:
            raise ValueError(f"unsupported renderer kind: {self.renderer_kind}")
        if self.renderer_kind == "procedural" and self.action_dimension != 8:
            raise ValueError("the procedural renderer requires action_dimension=8")

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("ART_OPTIMIZER_DATA_DIR", ".art-optimizer")).expanduser().resolve()
        return cls(
            data_dir=data_dir,
            database_path=Path(
                os.environ.get("ART_OPTIMIZER_DATABASE_PATH", str(data_dir / "art_optimizer.sqlite3"))
            ).expanduser().resolve(),
            artifacts_dir=Path(
                os.environ.get("ART_OPTIMIZER_ARTIFACTS_DIR", str(data_dir / "artifacts"))
            ).expanduser().resolve(),
            renderer_size=int(os.environ.get("ART_OPTIMIZER_IMAGE_SIZE", "640")),
            action_dimension=int(os.environ.get("ART_OPTIMIZER_ACTION_DIMENSION", "8")),
            candidate_count=int(os.environ.get("ART_OPTIMIZER_CANDIDATE_COUNT", "4")),
            renderer_kind=os.environ.get("ART_OPTIMIZER_RENDERER", "procedural").strip().lower(),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
