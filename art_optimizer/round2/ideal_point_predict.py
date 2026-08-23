from __future__ import annotations

import hashlib
import json
import math

import numpy as np
from scipy.special import ndtri
from scipy.stats import qmc

from .contracts import IdealPointProjection, PredictiveReceipt
from .ideal_point_math import FitPolicy, positive_definite

PREDICTIVE_REVISION = "scrambled-sobol-logistic-normal/v1"


def _slate_digest(alternative_ids: list[str], actions: np.ndarray) -> str:
    payload = {
        "alternative_ids": alternative_ids,
        "actions": np.asarray(actions, dtype=np.float64).astype(float).tolist(),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def predict_receipt(
    projection: IdealPointProjection,
    *,
    dimension: int,
    curvature: np.ndarray,
    policy: FitPolicy,
    engine_id: str,
    engine_revision: str,
    session_id: str,
    round_id: str,
    treatment_id: str,
    alternative_ids: list[str],
    actions: list[list[float]],
) -> PredictiveReceipt:
    values = np.asarray(actions, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != dimension:
        raise ValueError("prediction actions have the wrong dimension")
    if len(alternative_ids) != values.shape[0] or values.shape[0] < 2:
        raise ValueError("prediction alternatives are malformed")
    if not np.isfinite(values).all():
        raise ValueError("prediction actions must be finite")

    mean = np.asarray(projection.posterior_mean, dtype=np.float64)
    covariance = positive_definite(
        np.asarray(projection.posterior_covariance, dtype=np.float64),
        dimension=dimension,
        minimum_eigenvalue=policy.minimum_eigenvalue,
        name="posterior covariance",
    )
    linear = values @ curvature
    constants = -0.5 * np.einsum("ij,jk,ik->i", values, curvature, values)
    slate_digest = _slate_digest(alternative_ids, values)
    seed_material = (
        f"{projection.scope_id}\0{projection.source_event_cursor_digest}\0{slate_digest}"
    ).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little")

    sample_power = int(math.log2(policy.predictive_samples))
    sampler = qmc.Sobol(d=dimension, scramble=True, seed=seed)
    uniforms = sampler.random_base2(sample_power)
    normals = ndtri(np.clip(uniforms, 1e-10, 1.0 - 1e-10))
    targets = mean[None, :] + normals @ np.linalg.cholesky(covariance).T
    logits = (targets @ linear.T + constants[None, :]) / policy.temperature
    logits -= logits.max(axis=1, keepdims=True)
    probabilities = np.exp(logits)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    predictive = probabilities.mean(axis=0)
    predictive /= predictive.sum()
    entropy = float(-np.sum(predictive * np.log(np.maximum(predictive, 1e-15))))

    projection_revision = hashlib.sha256(
        (
            f"{engine_revision}\0{projection.source_event_cursor_digest}\0"
            f"{json.dumps(projection.posterior_mean, separators=(',', ':'))}"
        ).encode("utf-8")
    ).hexdigest()
    return PredictiveReceipt(
        session_id=session_id,
        round_id=round_id,
        treatment_id=treatment_id,
        engine_id=engine_id,
        engine_revision=engine_revision,
        projection_revision=projection_revision,
        scope_id=projection.scope_id,
        alternative_ids=alternative_ids,
        probabilities=predictive.astype(float).tolist(),
        entropy=entropy,
        source_event_cursor_digest=projection.source_event_cursor_digest,
        approximation_revision=PREDICTIVE_REVISION,
    )
