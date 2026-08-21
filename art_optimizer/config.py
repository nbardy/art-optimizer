from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .model_codec import get_model_profile, selected_model_id_from_env


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
        profile = get_model_profile(self.renderer_kind)
        profile.validate_size(self.renderer_size)
        if self.action_dimension != profile.action_dimension:
            raise ValueError(
                f"{profile.model_id} requires action_dimension={profile.action_dimension}"
            )
        if self.candidate_count != 4:
            raise ValueError("the v0 interaction requires exactly four candidates")

    @property
    def model_id(self) -> str:
        return self.renderer_kind

    @classmethod
    def from_env(cls) -> Settings:
        model_id = selected_model_id_from_env()
        profile = get_model_profile(model_id)
        root = Path(
            os.environ.get("ART_OPTIMIZER_DATA_DIR", ".art-optimizer")
        ).expanduser().resolve()
        source = os.environ.get("ART_OPTIMIZER_MODEL_SOURCE", profile.model_source)
        revision = os.environ.get("ART_OPTIMIZER_MODEL_REVISION", "unversioned")
        conditioning = os.environ.get(
            "ART_OPTIMIZER_CONDITIONING_MODE", profile.default_conditioning
        )
        runtime_identity = "\0".join(
            (model_id, source, revision, profile.codec_revision, conditioning)
        )
        runtime_fingerprint = hashlib.sha256(runtime_identity.encode("utf-8")).hexdigest()[:12]
        runtime_dir = (
            root
            if model_id == "procedural"
            else root / model_id / runtime_fingerprint
        )
        default_size = 640 if model_id == "procedural" else 1024
        return cls(
            data_dir=runtime_dir,
            database_path=Path(
                os.environ.get(
                    "ART_OPTIMIZER_DATABASE_PATH",
                    str(runtime_dir / "art_optimizer.sqlite3"),
                )
            ).expanduser().resolve(),
            artifacts_dir=Path(
                os.environ.get(
                    "ART_OPTIMIZER_ARTIFACTS_DIR",
                    str(runtime_dir / "artifacts"),
                )
            ).expanduser().resolve(),
            renderer_size=int(
                os.environ.get("ART_OPTIMIZER_IMAGE_SIZE", str(default_size))
            ),
            action_dimension=int(
                os.environ.get(
                    "ART_OPTIMIZER_ACTION_DIMENSION",
                    str(profile.action_dimension),
                )
            ),
            candidate_count=int(os.environ.get("ART_OPTIMIZER_CANDIDATE_COUNT", "4")),
            renderer_kind=model_id,
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
