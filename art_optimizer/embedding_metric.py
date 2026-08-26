from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .embedding_conditioning import EncodedPrompt
from .random_embedding_codec import (
    EmbeddingPathStep,
    direction_diagnostics,
    sample_unit_shell_directions,
)


RMS_METRIC_REVISION = "active-model-consumed-elements/v1"


def active_embedding_metric(base: EncodedPrompt) -> tuple[np.ndarray, float]:
    """Return the model-consumed element mask and prompt-embedding RMS.

    The metric is evaluated on the exact final prompt-embedding tensor supplied to
    the diffusion pipeline. When the pipeline exposes a token mask, padded/ignored
    positions are excluded rather than consuming part of the declared shell radius.
    """

    embeddings = _to_numpy(base.embeddings)
    if embeddings.ndim < 2 or embeddings.shape[0] != 1:
        raise ValueError("base prompt embeddings must have one batch element")
    values = np.asarray(embeddings[0], dtype=np.float64)
    active_mask = _broadcast_active_mask(base.mask, values.shape)
    active_values = values[active_mask]
    if active_values.size == 0:
        raise ValueError("prompt embedding mask contains no active elements")
    rms = float(np.sqrt(np.mean(np.square(active_values))))
    if not np.isfinite(rms) or rms < 1e-6:
        raise ValueError("active prompt embedding RMS is degenerate")
    return active_mask, rms


def active_candidate_offsets(
    shape: Sequence[int],
    *,
    codec_id: str,
    point_seed: int,
    radius: float,
    center_steps: Sequence[EmbeddingPathStep],
    active_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, object]]:
    """Build a deterministic shell walk in the active embedding metric."""

    normalized_shape = tuple(int(item) for item in shape)
    mask = np.asarray(active_mask, dtype=bool)
    if mask.shape != normalized_shape:
        raise ValueError("active embedding mask does not match embedding shape")
    active_count = int(mask.sum())
    if active_count < 4:
        raise ValueError("fewer than four active embedding elements are available")

    center = np.zeros(normalized_shape, dtype=np.float64)
    for step in center_steps:
        directions = active_shell_directions(
            normalized_shape,
            codec_id=step.codec_id,
            point_seed=step.point_seed,
            active_mask=mask,
        )
        center += float(step.radius) * directions[step.candidate_index]

    center_active = center[mask]
    center_rms = float(np.sqrt(np.mean(np.square(center_active))))
    if center_rms > 2.5:
        raise ValueError(
            "the accumulated embedding walk exceeds 2.5× active base RMS; "
            "step back or reset the center"
        )

    directions = active_shell_directions(
        normalized_shape,
        codec_id=codec_id,
        point_seed=point_seed,
        active_mask=mask,
    )
    points = center[None, ...] + float(radius) * directions

    compressed_directions = directions.reshape(4, -1)[:, mask.reshape(-1)]
    compressed_points = points.reshape(4, -1)[:, mask.reshape(-1)]
    diagnostics = direction_diagnostics(
        directions=compressed_directions,
        points=compressed_points,
        center=center_active,
        radius=float(radius),
    )
    diagnostics.update(
        {
            "rms_metric": RMS_METRIC_REVISION,
            "active_embedding_elements": active_count,
            "total_embedding_elements": int(mask.size),
            "active_embedding_fraction": float(active_count / mask.size),
        }
    )
    return points, diagnostics


def active_shell_directions(
    shape: Sequence[int],
    *,
    codec_id: str,
    point_seed: int,
    active_mask: np.ndarray,
) -> np.ndarray:
    """Project one codec slate into active elements and restore its invariants."""

    normalized_shape = tuple(int(item) for item in shape)
    mask = np.asarray(active_mask, dtype=bool)
    if mask.shape != normalized_shape:
        raise ValueError("active embedding mask does not match embedding shape")

    raw = sample_unit_shell_directions(
        normalized_shape,
        codec_id=codec_id,
        point_seed=point_seed,
    )
    flat = raw.reshape(4, -1)
    active = flat[:, mask.reshape(-1)].copy()

    if codec_id == "orthogonal-shell":
        active -= active.mean(axis=0, keepdims=True)
        q, _ = np.linalg.qr(active.T, mode="reduced")
        active = q.T
    elif codec_id == "antipodal-shell":
        first = active[0] - active[0].mean()
        first /= max(float(np.linalg.norm(first)), 1e-12)
        second = active[2] - active[2].mean()
        second -= float(second @ first) * first
        second /= max(float(np.linalg.norm(second)), 1e-12)
        active = np.stack((first, -first, second, -second), axis=0)
    elif codec_id == "gaussian-shell":
        active -= active.mean(axis=1, keepdims=True)

    rms = np.sqrt(np.mean(np.square(active), axis=1, keepdims=True))
    if np.any(rms < 1e-12):
        raise RuntimeError("active embedding projection produced a degenerate direction")
    active /= rms

    directions = np.zeros((4, int(mask.size)), dtype=np.float64)
    directions[:, mask.reshape(-1)] = active
    directions = directions.reshape((4, *normalized_shape))

    measured = np.sqrt(
        np.mean(
            np.square(directions.reshape(4, -1)[:, mask.reshape(-1)]),
            axis=1,
        )
    )
    if not np.allclose(measured, np.ones(4), atol=1e-10):
        raise RuntimeError("active embedding shell normalization failed")
    return directions


def _broadcast_active_mask(mask: Any | None, shape: tuple[int, ...]) -> np.ndarray:
    if mask is None:
        return np.ones(shape, dtype=bool)
    values = np.asarray(_to_numpy(mask), dtype=bool)
    if values.ndim > 0 and values.shape[0] == 1:
        values = values[0]
    while values.ndim < len(shape):
        values = np.expand_dims(values, axis=-1)
    try:
        return np.broadcast_to(values, shape).copy()
    except ValueError as error:
        raise ValueError(
            f"prompt mask shape {values.shape} cannot broadcast to embedding shape {shape}"
        ) from error


def _to_numpy(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value
    detach = getattr(value, "detach", None)
    if callable(detach):
        tensor = detach()
        cpu = getattr(tensor, "cpu", None)
        if callable(cpu):
            tensor = cpu()
        numpy = getattr(tensor, "numpy", None)
        if callable(numpy):
            return np.asarray(numpy())
    data = getattr(value, "data", None)
    if data is not None:
        return np.asarray(data)
    return np.asarray(value)
