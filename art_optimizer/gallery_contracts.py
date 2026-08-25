from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Self

import numpy as np
from pydantic import Field, field_validator, model_validator

from .domain import MAX_SEED, CommandPayload, utc_now
from .emergent_taste import ContractModel
from .rendering import artifact_manifest_path


GALLERY_EVENT_KIND = "emergent_taste_gallery_generated"
GALLERY_ACTIVATED_EVENT_KIND = "emergent_taste_gallery_cell_activated"
GALLERY_SESSION_EVENT_KIND = "emergent_taste_gallery_session_started"
DEFAULT_STRENGTHS = [0.25, 0.5, 0.75, 1.0, 1.25]


class TasteGalleryRequest(CommandPayload):
    row_count: int = Field(default=4, ge=1, le=6)
    strengths: list[float] = Field(
        default_factory=lambda: list(DEFAULT_STRENGTHS),
        min_length=2,
        max_length=7,
    )
    seed_nonce: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("strengths")
    @classmethod
    def validate_strengths(cls, value: list[float]) -> list[float]:
        normalized = [float(item) for item in value]
        if any(not np.isfinite(item) or not 0.0 <= item <= 3.0 for item in normalized):
            raise ValueError("gallery strengths must be finite values in [0, 3]")
        if len(normalized) != len(set(normalized)):
            raise ValueError("gallery strengths must be unique")
        return normalized


class TasteGalleryActivationPayload(CommandPayload):
    pass


class TasteGalleryCell(ContractModel):
    cell_id: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    seed: int = Field(ge=0, le=MAX_SEED)
    strength: float = Field(ge=0.0, le=3.0)
    action: list[float]
    clipped: bool
    design_id: str
    image_url: str
    image_digest: str
    image_path: str
    feature_vector: list[float]


class TasteGalleryManifest(ContractModel):
    gallery_id: str
    request_id: str
    source_session_id: str
    taste_id: str
    taste_label: str
    center: list[float]
    center_digest: str
    representation_scope_id: str
    representation_scope: dict[str, object]
    prompt: str
    renderer_revision: str
    row_count: int
    strengths: list[float]
    seeds: list[int]
    seed_nonce: int
    cells: list[TasteGalleryCell]
    preference_effect: str = "none"
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_grid(self) -> Self:
        expected = self.row_count * len(self.strengths)
        if len(self.cells) != expected:
            raise ValueError("gallery cell count does not match rows × strengths")
        if len(self.seeds) != self.row_count:
            raise ValueError("gallery seed count does not match row_count")
        ids = [item.cell_id for item in self.cells]
        if len(ids) != len(set(ids)):
            raise ValueError("gallery cell IDs must be unique")
        return self


def representation_scope(snapshot: dict[str, Any], capabilities: Any) -> dict[str, object]:
    current = snapshot["current_design"]
    manifest: dict[str, object] = {
        "schema": "taste-gallery-scope/v2",
        "model_id": capabilities.model_id,
        "renderer_revision": capabilities.renderer_revision,
        "codec_revision": capabilities.codec_revision,
        "conditioning_mode": capabilities.conditioning_mode,
        "control_basis_revision": current["control_basis_revision"],
        "prompt": snapshot["prompt"],
        "action_dimension": len(current["action"]),
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["scope_id"] = (
        f"taste-gallery-scope/v2:{hashlib.sha256(encoded.encode()).hexdigest()}"
    )
    return manifest


def gallery_id(
    *,
    session_id: str,
    taste_id: str,
    center_digest: str,
    scope_id: str,
    row_count: int,
    strengths: list[float],
    seed_nonce: int,
) -> str:
    encoded = json.dumps(
        {
            "session_id": session_id,
            "taste_id": taste_id,
            "center_digest": center_digest,
            "scope_id": scope_id,
            "row_count": row_count,
            "strengths": strengths,
            "seed_nonce": seed_nonce,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"taste_gallery_{hashlib.sha256(encoded.encode()).hexdigest()[:24]}"


def gallery_seeds(identity: str, current_seed: int, row_count: int) -> list[int]:
    seeds = [current_seed]
    for row in range(1, row_count):
        nonce = 0
        while True:
            material = f"{identity}:row:{row}:nonce:{nonce}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "little")
            seed &= MAX_SEED
            if seed not in seeds:
                seeds.append(seed)
                break
            nonce += 1
    return seeds


def cell_specs(
    *,
    identity: str,
    center: np.ndarray,
    seeds: list[int],
    strengths: list[float],
    artifacts_dir: Path,
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for row, seed in enumerate(seeds):
        for column, strength in enumerate(strengths):
            raw = center * float(strength)
            action = np.clip(raw, -1.0, 1.0)
            cell_id = f"cell-{row + 1}-{column + 1}"
            digest = hashlib.sha256(f"{identity}:{cell_id}".encode("utf-8")).hexdigest()
            design_id = f"gallery_{digest[:32]}"
            path = artifacts_dir / f"{design_id}.png"
            specs.append(
                {
                    "cell_id": cell_id,
                    "row": row,
                    "column": column,
                    "seed": seed,
                    "strength": float(strength),
                    "action": action,
                    "clipped": bool(np.any(np.abs(raw) > 1.0)),
                    "design_id": design_id,
                    "preexisting": path.exists() and artifact_manifest_path(path).exists(),
                }
            )
    return specs


def gallery_session_id(source_session_id: str, request_id: str) -> str:
    digest = hashlib.sha256(
        f"{source_session_id}:{request_id}".encode("utf-8")
    ).hexdigest()
    return f"session_{digest[:32]}"


def public_gallery(manifest: TasteGalleryManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    for cell in payload["cells"]:
        cell.pop("image_path", None)
        cell.pop("feature_vector", None)
    payload["axis"] = {
        "vertical": "seed",
        "horizontal": "taste strength",
        "strength_formula": "clip(strength × taste_center, -1, 1)",
    }
    return payload
