from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal, Sequence

import numpy as np


RandomEmbeddingCodecId = Literal[
    "gaussian-shell",
    "orthogonal-shell",
    "low-rank-shell",
    "antipodal-shell",
]


@dataclass(frozen=True, slots=True)
class RandomEmbeddingCodecProfile:
    codec_id: RandomEmbeddingCodecId
    label: str
    description: str
    geometry: str
    default_radius: float
    minimum_radius: float = 0.05
    maximum_radius: float = 1.50
    low_rank: int = 4
    revision: str = "random-embedding-shell/v1"

    def public_metadata(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EmbeddingPathStep:
    codec_id: RandomEmbeddingCodecId
    point_seed: int
    candidate_index: int
    radius: float

    def __post_init__(self) -> None:
        get_random_embedding_codec(self.codec_id)
        if not 0 <= self.point_seed <= (1 << 63) - 1:
            raise ValueError("point_seed is outside the supported range")
        if not 0 <= self.candidate_index < 4:
            raise ValueError("candidate_index must be 0, 1, 2, or 3")
        if not math.isfinite(self.radius) or not 0.0 < self.radius <= 1.5:
            raise ValueError("radius must be finite and lie in (0, 1.5]")

    def public_metadata(self) -> dict[str, object]:
        return asdict(self)


_PROFILES: dict[str, RandomEmbeddingCodecProfile] = {
    "gaussian-shell": RandomEmbeddingCodecProfile(
        codec_id="gaussian-shell",
        label="Gaussian shell",
        description=(
            "Four independent full-tensor Gaussian directions, each normalized onto "
            "the same nonzero RMS shell. In high dimension they are already nearly orthogonal."
        ),
        geometry="iid full-tensor Gaussian directions normalized to a fixed RMS radius",
        default_radius=0.40,
    ),
    "orthogonal-shell": RandomEmbeddingCodecProfile(
        codec_id="orthogonal-shell",
        label="Orthogonal shell",
        description=(
            "Four full-tensor Gaussian directions explicitly orthogonalized before "
            "normalization. This maximizes controlled separation at a matched radius."
        ),
        geometry="QR-orthogonal full-tensor directions on a fixed RMS shell",
        default_radius=0.40,
    ),
    "low-rank-shell": RandomEmbeddingCodecProfile(
        codec_id="low-rank-shell",
        label="Low-rank shell",
        description=(
            "Random token-by-channel perturbations generated from a small matrix factorization. "
            "They stay far from the center but are structurally smoother than elementwise noise."
        ),
        geometry="rank-4 token-channel Gaussian factors normalized to a fixed RMS shell",
        default_radius=0.50,
        low_rank=4,
    ),
    "antipodal-shell": RandomEmbeddingCodecProfile(
        codec_id="antipodal-shell",
        label="Antipodal cross",
        description=(
            "Two orthogonal random directions shown with both signs: +u, -u, +v, -v. "
            "This tests whether a random line has a coherent signed visual effect."
        ),
        geometry="two orthogonal full-tensor directions with exact positive/negative pairs",
        default_radius=0.40,
    ),
}


def random_embedding_codec_catalog() -> list[dict[str, object]]:
    return [profile.public_metadata() for profile in _PROFILES.values()]


def available_random_embedding_codecs() -> tuple[str, ...]:
    return tuple(_PROFILES)


def get_random_embedding_codec(codec_id: str) -> RandomEmbeddingCodecProfile:
    profile = _PROFILES.get(codec_id)
    if profile is None:
        choices = ", ".join(_PROFILES)
        raise ValueError(f"unknown random embedding codec {codec_id!r}; choose one of: {choices}")
    return profile


def sample_unit_shell_directions(
    shape: Sequence[int],
    *,
    codec_id: str,
    point_seed: int,
    candidate_count: int = 4,
) -> np.ndarray:
    """Return candidate perturbations with exactly unit RMS and no center sample."""

    profile = get_random_embedding_codec(codec_id)
    normalized_shape = tuple(int(item) for item in shape)
    if not normalized_shape or any(item <= 0 for item in normalized_shape):
        raise ValueError("embedding shape must contain positive dimensions")
    if candidate_count != 4:
        raise ValueError("the direction lab currently requires exactly four candidates")
    if not 0 <= point_seed <= (1 << 63) - 1:
        raise ValueError("point_seed is outside the supported range")

    rng = np.random.default_rng(point_seed)
    element_count = int(np.prod(normalized_shape))
    if element_count < candidate_count:
        raise ValueError("embedding representation is too small for four shell directions")

    if profile.codec_id == "gaussian-shell":
        directions = rng.standard_normal((candidate_count, *normalized_shape))
        directions = _remove_constant_mode(directions)
        return _normalize_rms(directions)

    if profile.codec_id == "orthogonal-shell":
        matrix = rng.standard_normal((element_count, candidate_count))
        matrix -= matrix.mean(axis=0, keepdims=True)
        q, _ = np.linalg.qr(matrix, mode="reduced")
        directions = q.T.reshape((candidate_count, *normalized_shape))
        return _normalize_rms(directions)

    if profile.codec_id == "low-rank-shell":
        if len(normalized_shape) == 1:
            directions = rng.standard_normal((candidate_count, *normalized_shape))
            directions = _remove_constant_mode(directions)
        else:
            token_count = int(np.prod(normalized_shape[:-1]))
            channel_count = normalized_shape[-1]
            rank = max(1, min(profile.low_rank, token_count, channel_count))
            directions = np.empty((candidate_count, token_count, channel_count), dtype=np.float64)
            for index in range(candidate_count):
                token_factors = rng.standard_normal((token_count, rank))
                token_factors -= token_factors.mean(axis=0, keepdims=True)
                channel_factors = rng.standard_normal((rank, channel_count))
                directions[index] = token_factors @ channel_factors / math.sqrt(rank)
            directions = directions.reshape((candidate_count, *normalized_shape))
        return _normalize_rms(directions)

    if profile.codec_id == "antipodal-shell":
        vectors = rng.standard_normal((2, element_count))
        vectors -= vectors.mean(axis=1, keepdims=True)
        first = vectors[0]
        first /= max(float(np.linalg.norm(first)), 1e-12)
        second = vectors[1] - float(vectors[1] @ first) * first
        second /= max(float(np.linalg.norm(second)), 1e-12)
        directions = np.stack((first, -first, second, -second), axis=0)
        directions = directions.reshape((candidate_count, *normalized_shape))
        return _normalize_rms(directions)

    raise AssertionError(f"unhandled codec: {profile.codec_id}")


def reconstruct_center_offset(
    shape: Sequence[int],
    steps: Sequence[EmbeddingPathStep],
) -> np.ndarray:
    normalized_shape = tuple(int(item) for item in shape)
    offset = np.zeros(normalized_shape, dtype=np.float64)
    for step in steps:
        directions = sample_unit_shell_directions(
            normalized_shape,
            codec_id=step.codec_id,
            point_seed=step.point_seed,
        )
        offset += step.radius * directions[step.candidate_index]
    return offset


def candidate_offsets(
    shape: Sequence[int],
    *,
    codec_id: str,
    point_seed: int,
    radius: float,
    center_steps: Sequence[EmbeddingPathStep] = (),
) -> tuple[np.ndarray, dict[str, object]]:
    profile = get_random_embedding_codec(codec_id)
    if not math.isfinite(radius) or not profile.minimum_radius <= radius <= profile.maximum_radius:
        raise ValueError(
            f"{profile.codec_id} radius must lie in "
            f"[{profile.minimum_radius}, {profile.maximum_radius}]"
        )
    center = reconstruct_center_offset(shape, center_steps)
    center_rms = float(np.sqrt(np.mean(np.square(center))))
    if center_rms > 2.5:
        raise ValueError(
            "the accumulated embedding walk exceeds 2.5× base RMS; step back or reset the center"
        )
    directions = sample_unit_shell_directions(
        shape,
        codec_id=codec_id,
        point_seed=point_seed,
    )
    points = center[None, ...] + float(radius) * directions
    diagnostics = direction_diagnostics(
        directions=directions,
        points=points,
        center=center,
        radius=float(radius),
    )
    return points, diagnostics


def direction_diagnostics(
    *,
    directions: np.ndarray,
    points: np.ndarray,
    center: np.ndarray,
    radius: float,
) -> dict[str, object]:
    flat_directions = np.asarray(directions, dtype=np.float64).reshape(directions.shape[0], -1)
    flat_points = np.asarray(points, dtype=np.float64).reshape(points.shape[0], -1)
    norms = np.linalg.norm(flat_directions, axis=1)
    cosine = (flat_directions @ flat_directions.T) / np.maximum(
        norms[:, None] * norms[None, :],
        1e-12,
    )
    singular_values = np.linalg.svd(flat_directions, compute_uv=False)
    squared = np.square(singular_values)
    effective_rank = float(np.square(squared.sum()) / max(np.square(squared).sum(), 1e-12))

    pairwise_rms: list[float] = []
    for left in range(flat_points.shape[0]):
        for right in range(left + 1, flat_points.shape[0]):
            pairwise_rms.append(
                float(np.sqrt(np.mean(np.square(flat_points[left] - flat_points[right]))))
            )

    candidate_rms = np.sqrt(np.mean(np.square(flat_points), axis=1))
    return {
        "radius_relative_to_base_rms": float(radius),
        "center_offset_rms_relative_to_base": float(
            np.sqrt(np.mean(np.square(np.asarray(center, dtype=np.float64))))
        ),
        "candidate_offset_rms_relative_to_base": candidate_rms.astype(float).tolist(),
        "direction_cosine_matrix": cosine.astype(float).tolist(),
        "direction_effective_rank": effective_rank,
        "pairwise_candidate_rms": pairwise_rms,
        "minimum_pairwise_candidate_rms": float(min(pairwise_rms)),
        "maximum_pairwise_candidate_rms": float(max(pairwise_rms)),
    }


def embedding_walk_digest(
    *,
    prompt: str,
    image_seed: int,
    codec_id: str,
    point_seed: int,
    radius: float,
    center_steps: Sequence[EmbeddingPathStep],
) -> str:
    payload = {
        "schema": "random-embedding-walk/v1",
        "prompt": " ".join(prompt.split()),
        "image_seed": int(image_seed),
        "codec_id": codec_id,
        "point_seed": int(point_seed),
        "radius": float(radius),
        "center_steps": [step.public_metadata() for step in center_steps],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _remove_constant_mode(directions: np.ndarray) -> np.ndarray:
    flat = np.asarray(directions, dtype=np.float64).reshape(directions.shape[0], -1)
    flat = flat - flat.mean(axis=1, keepdims=True)
    return flat.reshape(directions.shape)


def _normalize_rms(directions: np.ndarray) -> np.ndarray:
    values = np.asarray(directions, dtype=np.float64)
    axes = tuple(range(1, values.ndim))
    rms = np.sqrt(np.mean(np.square(values), axis=axes, keepdims=True))
    if np.any(rms < 1e-12):
        raise RuntimeError("random embedding codec generated a degenerate direction")
    normalized = values / rms
    if np.any(np.sqrt(np.mean(np.square(normalized), axis=axes)) < 0.999999):
        raise RuntimeError("random embedding direction normalization failed")
    return normalized
