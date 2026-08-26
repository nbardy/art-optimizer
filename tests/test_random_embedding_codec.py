from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
from PIL import Image

from art_optimizer.diffusers_renderer import LocalDiffusersRenderer
from art_optimizer.model_codec import get_codec
from art_optimizer.random_embedding_codec import (
    EmbeddingPathStep,
    available_random_embedding_codecs,
    candidate_offsets,
    sample_unit_shell_directions,
)


def rms(values: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean(np.square(values), axis=tuple(range(1, values.ndim))))


def test_all_random_codecs_are_deterministic_noncentral_unit_shells() -> None:
    for codec_id in available_random_embedding_codecs():
        first = sample_unit_shell_directions(
            (12, 16),
            codec_id=codec_id,
            point_seed=12345,
        )
        second = sample_unit_shell_directions(
            (12, 16),
            codec_id=codec_id,
            point_seed=12345,
        )
        np.testing.assert_allclose(first, second)
        np.testing.assert_allclose(rms(first), np.ones(4), atol=1e-10)
        assert np.min(np.linalg.norm(first.reshape(4, -1), axis=1)) > 1.0
        assert np.max(np.abs(first.mean(axis=(1, 2)))) < 1e-12


def test_orthogonal_and_antipodal_geometry_is_exact() -> None:
    orthogonal = sample_unit_shell_directions(
        (10, 20),
        codec_id="orthogonal-shell",
        point_seed=7,
    ).reshape(4, -1)
    normalized = orthogonal / np.linalg.norm(orthogonal, axis=1, keepdims=True)
    np.testing.assert_allclose(normalized @ normalized.T, np.eye(4), atol=1e-10)

    antipodal = sample_unit_shell_directions(
        (10, 20),
        codec_id="antipodal-shell",
        point_seed=9,
    )
    np.testing.assert_allclose(antipodal[0], -antipodal[1], atol=1e-12)
    np.testing.assert_allclose(antipodal[2], -antipodal[3], atol=1e-12)
    assert abs(float(np.vdot(antipodal[0], antipodal[2]))) < 1e-10


def test_low_rank_codec_really_has_low_token_channel_rank() -> None:
    directions = sample_unit_shell_directions(
        (18, 32),
        codec_id="low-rank-shell",
        point_seed=808,
    )
    assert all(np.linalg.matrix_rank(direction, tol=1e-9) <= 4 for direction in directions)


def test_embedding_walk_moves_the_center_and_never_adds_a_center_candidate() -> None:
    step = EmbeddingPathStep(
        codec_id="orthogonal-shell",
        point_seed=11,
        candidate_index=2,
        radius=0.4,
    )
    points, diagnostics = candidate_offsets(
        (20, 24),
        codec_id="gaussian-shell",
        point_seed=12,
        radius=0.5,
        center_steps=[step],
    )
    assert abs(diagnostics["center_offset_rms_relative_to_base"] - 0.4) < 1e-10
    assert np.min(rms(points)) > 0.1
    assert diagnostics["minimum_pairwise_candidate_rms"] > 0.3


class FakeTensor:
    def __init__(self, data, dtype="float32", device="cpu"):
        self.data = np.asarray(data)
        self.dtype = dtype
        self.device = device

    @property
    def shape(self):
        return self.data.shape

    def clone(self):
        return FakeTensor(self.data.copy(), self.dtype, self.device)

    def __getitem__(self, item):
        return FakeTensor(self.data[item], self.dtype, self.device)

    def any(self, *, dim, keepdim):
        return FakeTensor(
            self.data.any(axis=dim, keepdims=keepdim),
            "bool",
            self.device,
        )

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

    def __sub__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data - value, self.dtype, self.device)

    def __mul__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data * value, self.dtype, self.device)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data / value, self.dtype, self.device)


class FakeGenerator:
    def __init__(self, device):
        self.device = device
        self.seed = None

    def manual_seed(self, seed):
        self.seed = seed
        return self


class FakeTorch:
    Generator = FakeGenerator

    @staticmethod
    def inference_mode():
        return nullcontext()

    @staticmethod
    def as_tensor(values, *, device, dtype):
        return FakeTensor(np.asarray(values), dtype, device)


class FakeKreaPipeline:
    def __init__(self):
        self.calls: list[dict] = []
        self.encode_calls = 0

    def encode_prompt(self, *, prompt):
        self.encode_calls += 1
        values = [float(sum(item.encode("utf-8")) % 31 + 2) for item in prompt]
        embedding = FakeTensor(
            np.stack([np.full((8, 3, 5), value) for value in values])
        )
        mask = FakeTensor(np.ones((len(prompt), 8), dtype=bool), "bool")
        return embedding, mask

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        data = kwargs["prompt_embeds"].data
        red = int(abs(float(data[..., 0].mean())) * 11) % 255
        green = int(abs(float(data[..., 1].mean())) * 17) % 255
        blue = int(abs(float(data[..., 2].mean())) * 23) % 255
        return SimpleNamespace(images=[Image.new("RGB", (256, 256), (red, green, blue))])


def test_diffusers_renderer_executes_four_non_string_fixed_seed_points(tmp_path) -> None:
    pipeline = FakeKreaPipeline()
    renderer = LocalDiffusersRenderer(
        tmp_path,
        256,
        get_codec("krea2-turbo"),
        device="cpu",
        dtype="float32",
        conditioning_mode="embedding",
        pipeline=pipeline,
        torch_module=FakeTorch(),
    )
    result = renderer.render_embedding_slate(
        design_ids=["point-1", "point-2", "point-3", "point-4"],
        image_seed=77,
        prompt="a strange mechanical flower",
        codec_id="orthogonal-shell",
        point_seed=909,
        radius=0.4,
        center_steps=[],
    )

    assert len(result["artifacts"]) == 4
    assert len(pipeline.calls) == 4
    assert pipeline.encode_calls == 1
    assert {call["generator"].seed for call in pipeline.calls} == {77}
    assert result["diagnostics"]["string_axes_used"] is False
    assert result["diagnostics"]["minimum_pairwise_candidate_rms"] > 0.5

    cached = renderer.render_embedding_slate(
        design_ids=["point-1", "point-2", "point-3", "point-4"],
        image_seed=77,
        prompt="a strange mechanical flower",
        codec_id="orthogonal-shell",
        point_seed=909,
        radius=0.4,
        center_steps=[],
    )
    assert len(cached["artifacts"]) == 4
    assert len(pipeline.calls) == 4
