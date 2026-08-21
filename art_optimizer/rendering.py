from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Protocol, runtime_checkable
from uuid import uuid4

import numpy as np
from PIL import Image

_SAFE_DESIGN_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
ReplayLevel = Literal["exact", "best_effort"]


@dataclass(frozen=True)
class RendererCapabilities:
    model_id: str
    action_dimension: int
    deterministic: bool
    supports_batching: bool
    renderer_revision: str
    codec_revision: str
    control_basis_revision: str
    feature_revision: str
    replay_level: ReplayLevel
    display_name: str = ""
    model_source: str = ""
    license_id: str = ""
    license_url: str = ""
    open_weights: bool = False
    osi_open_source: bool = False
    content_filter_required: bool = False
    conditioning_mode: str = "native"
    supports_embedding_control: bool = False


@dataclass(slots=True)
class RenderedArtifact:
    path: Path
    feature_vector: list[float]
    digest: str
    request_digest: str = ""


@runtime_checkable
class ImageRenderer(Protocol):
    revision: str
    codec_revision: str
    control_basis_revision: str
    feature_revision: str
    action_dimension: int

    def capabilities(self) -> RendererCapabilities: ...

    def render(
        self,
        *,
        design_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
    ) -> RenderedArtifact: ...


def validate_render_input(
    *,
    design_id: str,
    seed: int,
    action: np.ndarray,
    action_dimension: int,
) -> np.ndarray:
    if not _SAFE_DESIGN_ID.fullmatch(design_id):
        raise ValueError("design_id contains unsafe path characters")
    if not 0 <= seed <= (1 << 63) - 1:
        raise ValueError("seed is outside the supported range")
    values = np.asarray(action, dtype=np.float64)
    if values.shape != (action_dimension,):
        raise ValueError(f"renderer expects exactly {action_dimension} controls")
    if not np.isfinite(values).all():
        raise ValueError("renderer action must be finite")
    return np.clip(values, -1.0, 1.0)


def render_request_digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_features(image: Image.Image | np.ndarray) -> list[float]:
    if isinstance(image, Image.Image):
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    else:
        rgb = np.asarray(image, dtype=np.float32)
        if rgb.max(initial=0.0) > 1.0:
            rgb = rgb / 255.0
    mean = rgb.mean(axis=(0, 1))
    std = rgb.std(axis=(0, 1))
    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-4)
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    edge_x = float(np.abs(np.diff(luminance, axis=1)).mean())
    edge_y = float(np.abs(np.diff(luminance, axis=0)).mean())
    horizontal_symmetry = float(1.0 - np.abs(rgb - rgb[:, ::-1]).mean())
    vertical_symmetry = float(1.0 - np.abs(rgb - rgb[::-1, :]).mean())
    features = np.concatenate(
        [
            mean,
            std,
            np.asarray(
                [
                    saturation.mean(),
                    saturation.std(),
                    luminance.std(),
                    edge_x * 4.0,
                    edge_y * 4.0,
                    horizontal_symmetry,
                    vertical_symmetry,
                ],
                dtype=np.float32,
            ),
        ]
    )
    return np.clip(features, 0.0, 1.0).astype(float).tolist()


def load_cached_artifact(path: Path, expected_request_digest: str) -> RenderedArtifact | None:
    manifest_path = artifact_manifest_path(path)
    if not path.exists() or not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("request_digest") != expected_request_digest:
        return None
    digest = file_digest(path)
    if manifest.get("image_digest") != digest:
        return None
    with Image.open(path) as stored:
        image = stored.convert("RGB")
        features = image_features(image)
    return RenderedArtifact(
        path=path,
        feature_vector=features,
        digest=digest,
        request_digest=expected_request_digest,
    )


def save_rendered_artifact(
    image: Image.Image,
    path: Path,
    *,
    request_digest: str,
    metadata: Mapping[str, object],
) -> RenderedArtifact:
    image = image.convert("RGB")
    atomic_save_png(image, path)
    digest = file_digest(path)
    manifest = {
        "schema": "art-optimizer-render/v1",
        "request_digest": request_digest,
        "image_digest": digest,
        "metadata": dict(metadata),
    }
    atomic_write_json(artifact_manifest_path(path), manifest)
    return RenderedArtifact(
        path=path,
        feature_vector=image_features(image),
        digest=digest,
        request_digest=request_digest,
    )


def artifact_manifest_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.json")


def atomic_save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        image.convert("RGB").save(temporary, format="PNG", optimize=True)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
