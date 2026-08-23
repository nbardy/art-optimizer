from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image

from .contracts import PerceptualSlateReceipt

PERCEPTUAL_REVISION = "handcrafted-spatial-color-edge-194d/v1"


def _load_rgb(source: str | Path | Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(source, Image.Image):
        image = source.convert("RGB")
    elif isinstance(source, (str, Path)):
        with Image.open(source) as loaded:
            image = loaded.convert("RGB")
    else:
        values = np.asarray(source)
        if values.ndim != 3 or values.shape[2] != 3:
            raise ValueError("image array must have shape H x W x 3")
        if values.dtype != np.uint8:
            scale = 255.0 if float(values.max(initial=0.0)) <= 1.0 else 1.0
            values = np.clip(values * scale, 0.0, 255.0).astype(np.uint8)
        image = Image.fromarray(values, mode="RGB")
    resampling = getattr(Image, "Resampling", Image)
    return np.asarray(
        image.resize((32, 32), resampling.BILINEAR),
        dtype=np.float64,
    ) / 255.0


def _pool(values: np.ndarray, rows: int, columns: int) -> np.ndarray:
    height, width = values.shape[:2]
    if height % rows or width % columns:
        raise ValueError("pooled dimensions must divide the image")
    reshaped = values.reshape(
        rows,
        height // rows,
        columns,
        width // columns,
        *values.shape[2:],
    )
    return reshaped.mean(axis=(1, 3))


def image_embedding(
    source: str | Path | Image.Image | np.ndarray,
) -> np.ndarray:
    """Return a deterministic output-space diagnostic embedding.

    This is intentionally not called a learned visual representation. It mixes
    coarse luminance/chroma layout, color histograms, and oriented edge energy
    so duplicate detection is materially stronger than the legacy 13-value
    global summary while remaining dependency-light and replayable.
    """

    rgb = _load_rgb(source)
    luminance = (
        0.2126 * rgb[..., 0]
        + 0.7152 * rgb[..., 1]
        + 0.0722 * rgb[..., 2]
    )
    red_green = rgb[..., 0] - rgb[..., 1]
    blue_yellow = rgb[..., 2] - 0.5 * (rgb[..., 0] + rgb[..., 1])

    luminance_layout = _pool(luminance[..., None], 8, 8).reshape(-1)
    chroma = np.stack([red_green, blue_yellow], axis=2)
    chroma_layout = _pool(chroma, 4, 4).reshape(-1)

    histograms = []
    for channel in range(3):
        histogram, _ = np.histogram(
            rgb[..., channel],
            bins=8,
            range=(0.0, 1.0),
            density=False,
        )
        histogram = histogram.astype(np.float64)
        histogram /= max(histogram.sum(), 1.0)
        histograms.append(histogram)
    color_histogram = np.concatenate(histograms)

    gradient_x = np.zeros_like(luminance)
    gradient_y = np.zeros_like(luminance)
    gradient_x[:, 1:-1] = (luminance[:, 2:] - luminance[:, :-2]) * 0.5
    gradient_y[1:-1, :] = (luminance[2:, :] - luminance[:-2, :]) * 0.5
    magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
    angle = np.mod(np.arctan2(gradient_y, gradient_x), np.pi)
    oriented = []
    centers = np.linspace(0.0, np.pi, 4, endpoint=False)
    for center in centers:
        distance = np.abs(angle - center)
        distance = np.minimum(distance, np.pi - distance)
        weight = np.clip(1.0 - distance / (np.pi / 4.0), 0.0, 1.0)
        oriented.append(_pool((magnitude * weight)[..., None], 4, 4).reshape(-1))
    edge_layout = np.concatenate(oriented)

    global_statistics = np.concatenate(
        [
            rgb.mean(axis=(0, 1)),
            rgb.std(axis=(0, 1)),
            np.asarray(
                [
                    luminance.mean(),
                    luminance.std(),
                    magnitude.mean(),
                    magnitude.std(),
                ],
                dtype=np.float64,
            ),
        ]
    )

    vector = np.concatenate(
        [
            luminance_layout,
            chroma_layout,
            color_histogram,
            edge_layout,
            global_statistics,
        ]
    )
    vector -= vector.mean()
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        vector = np.zeros_like(vector)
        vector[0] = 1.0
    else:
        vector /= norm
    return vector.astype(np.float64)


def cosine_distance(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("perceptual vectors must be aligned one-dimensional arrays")
    left_norm = float(np.linalg.norm(a))
    right_norm = float(np.linalg.norm(b))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 1.0
    similarity = float(np.dot(a, b) / (left_norm * right_norm))
    return float(np.clip(1.0 - similarity, 0.0, 2.0))


def slate_receipt(
    *,
    session_id: str,
    round_id: str,
    anchor_id: str,
    anchor_embedding: np.ndarray,
    candidate_embeddings: Mapping[str, np.ndarray],
    duplicate_threshold: float = 0.025,
    repaired_candidate_ids: list[str] | None = None,
) -> PerceptualSlateReceipt:
    if duplicate_threshold <= 0.0:
        raise ValueError("duplicate threshold must be positive")
    candidate_ids = list(candidate_embeddings)
    embeddings = {
        candidate_id: np.asarray(candidate_embeddings[candidate_id], dtype=np.float64)
        for candidate_id in candidate_ids
    }
    anchor = np.asarray(anchor_embedding, dtype=np.float64)
    distance_matrix: list[list[float]] = []
    for left_id in candidate_ids:
        distance_matrix.append(
            [
                cosine_distance(embeddings[left_id], embeddings[right_id])
                for right_id in candidate_ids
            ]
        )

    anchor_distances = {
        candidate_id: cosine_distance(anchor, embedding)
        for candidate_id, embedding in embeddings.items()
    }

    parent: dict[str, str] = {candidate_id: candidate_id for candidate_id in candidate_ids}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        winner, loser = sorted((left_root, right_root))
        parent[loser] = winner

    duplicate_of: dict[str, str] = {}
    for index, candidate_id in enumerate(candidate_ids):
        if anchor_distances[candidate_id] <= duplicate_threshold:
            duplicate_of[candidate_id] = anchor_id
        for previous_index in range(index):
            previous_id = candidate_ids[previous_index]
            if distance_matrix[index][previous_index] <= duplicate_threshold:
                union(candidate_id, previous_id)
                duplicate_of.setdefault(candidate_id, previous_id)

    equivalence_classes: dict[str, str] = {}
    for candidate_id in candidate_ids:
        if duplicate_of.get(candidate_id) == anchor_id:
            equivalence_classes[candidate_id] = f"perceptual_{anchor_id}"
            continue
        root = find(candidate_id)
        digest = hashlib.sha256(
            f"{round_id}\0{root}".encode("utf-8")
        ).hexdigest()[:20]
        equivalence_classes[candidate_id] = f"perceptual_{digest}"

    return PerceptualSlateReceipt(
        session_id=session_id,
        round_id=round_id,
        revision=PERCEPTUAL_REVISION,
        candidate_ids=candidate_ids,
        distance_matrix=distance_matrix,
        anchor_distances=anchor_distances,
        equivalence_classes=equivalence_classes,
        duplicate_of=duplicate_of,
        repaired_candidate_ids=repaired_candidate_ids or [],
    )
