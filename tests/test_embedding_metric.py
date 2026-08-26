from __future__ import annotations

import numpy as np

from art_optimizer.embedding_conditioning import EncodedPrompt, apply_relative_rms_offset
from art_optimizer.embedding_metric import (
    RMS_METRIC_REVISION,
    active_candidate_offsets,
    active_embedding_metric,
)
from art_optimizer.model_codec import get_codec


class FakeTensor:
    def __init__(self, data, dtype="float32", device="cpu"):
        self.data = np.asarray(data)
        self.dtype = dtype
        self.device = device

    @property
    def shape(self):
        return self.data.shape

    def float(self):
        return FakeTensor(self.data.astype(np.float64), "float32", self.device)

    def square(self):
        return FakeTensor(np.square(self.data), self.dtype, self.device)

    def mean(self):
        return FakeTensor(np.asarray(self.data.mean()), self.dtype, self.device)

    def sqrt(self):
        return FakeTensor(np.sqrt(self.data), self.dtype, self.device)

    def clamp_min(self, value):
        return FakeTensor(np.maximum(self.data, value), self.dtype, self.device)

    def to(self, *, dtype=None, device=None):
        return FakeTensor(
            self.data.copy(),
            dtype or self.dtype,
            device or self.device,
        )

    def unsqueeze(self, dim):
        return FakeTensor(np.expand_dims(self.data, axis=dim), self.dtype, self.device)

    def item(self):
        return self.data.item()

    def __add__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data + value, self.dtype, self.device)

    def __mul__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data * value, self.dtype, self.device)

    def __rmul__(self, other):
        return self * other


class FakeTorch:
    @staticmethod
    def as_tensor(values, *, device, dtype):
        return FakeTensor(np.asarray(values), dtype, device)


def test_active_metric_ignores_masked_embedding_positions() -> None:
    values = np.empty((1, 6, 2), dtype=np.float32)
    values[:, :3, :] = 2.0
    values[:, 3:, :] = 100.0
    base = EncodedPrompt(
        embeddings=FakeTensor(values),
        mask=FakeTensor([[True, True, True, False, False, False]], "bool"),
    )

    active_mask, base_rms = active_embedding_metric(base)

    assert base_rms == 2.0
    assert active_mask.shape == (6, 2)
    assert int(active_mask.sum()) == 6
    assert not active_mask[3:].any()


def test_active_orthogonal_shell_has_exact_radius_and_zero_masked_energy() -> None:
    mask = np.zeros((6, 2), dtype=bool)
    mask[:3, :] = True
    points, diagnostics = active_candidate_offsets(
        (6, 2),
        codec_id="orthogonal-shell",
        point_seed=123,
        radius=0.4,
        center_steps=[],
        active_mask=mask,
    )

    assert np.count_nonzero(points[:, ~mask]) == 0
    active = points.reshape(4, -1)[:, mask.reshape(-1)]
    np.testing.assert_allclose(
        np.sqrt(np.mean(np.square(active), axis=1)),
        np.full(4, 0.4),
        atol=1e-10,
    )
    normalized = active / np.linalg.norm(active, axis=1, keepdims=True)
    np.testing.assert_allclose(normalized @ normalized.T, np.eye(4), atol=1e-10)
    assert diagnostics["rms_metric"] == RMS_METRIC_REVISION
    assert diagnostics["active_embedding_elements"] == 6
    assert diagnostics["total_embedding_elements"] == 12
    assert diagnostics["active_embedding_fraction"] == 0.5


def test_applied_offset_preserves_masked_tokens_and_matches_active_radius() -> None:
    values = np.empty((1, 6, 2), dtype=np.float32)
    values[:, :3, :] = 2.0
    values[:, 3:, :] = 100.0
    base = EncodedPrompt(
        embeddings=FakeTensor(values),
        mask=FakeTensor([[True, True, True, False, False, False]], "bool"),
    )
    active_mask, base_rms = active_embedding_metric(base)
    points, _ = active_candidate_offsets(
        (6, 2),
        codec_id="orthogonal-shell",
        point_seed=456,
        radius=0.4,
        center_steps=[],
        active_mask=active_mask,
    )
    request = get_codec("krea2-turbo").compile(
        base_prompt="a masked geometry test",
        action=np.zeros(8),
        seed=7,
        size=256,
    )

    conditioning, measured = apply_relative_rms_offset(
        request,
        base,
        points[0],
        FakeTorch(),
        active_mask=active_mask,
        base_rms=base_rms,
    )

    mixed = conditioning["prompt_embeds"].data[0]
    delta = mixed - values[0]
    np.testing.assert_allclose(mixed[~active_mask], values[0][~active_mask])
    assert measured == 2.0
    assert np.isclose(
        np.sqrt(np.mean(np.square(delta[active_mask]))) / measured,
        0.4,
        atol=1e-6,
    )
