from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
from PIL import Image

from art_optimizer.diffusers_renderer import LocalDiffusersRenderer
from art_optimizer.embedding_conditioning import apply_direction_bank, build_direction_bank
from art_optimizer.model_codec import (
    available_model_ids,
    get_codec,
    get_model_profile,
    model_catalog,
)


class FakeTensor:
    def __init__(self, data, dtype="float32"):
        self.data = np.asarray(data)
        self.dtype = dtype

    def clone(self):
        return FakeTensor(self.data.copy(), self.dtype)

    def __getitem__(self, item):
        return FakeTensor(self.data[item], self.dtype)

    def any(self, *, dim, keepdim):
        return FakeTensor(self.data.any(axis=dim, keepdims=keepdim), "bool")

    def float(self):
        return FakeTensor(self.data.astype(np.float64), "float32")

    def square(self):
        return FakeTensor(np.square(self.data), self.dtype)

    def mean(self):
        return FakeTensor(np.asarray(self.data.mean()), self.dtype)

    def sqrt(self):
        return FakeTensor(np.sqrt(self.data), self.dtype)

    def clamp_min(self, value):
        return FakeTensor(np.maximum(self.data, value), self.dtype)

    def to(self, *, dtype=None):
        return FakeTensor(self.data.copy(), dtype or self.dtype)

    def __add__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data + value, self.dtype)

    def __sub__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data - value, self.dtype)

    def __mul__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data * value, self.dtype)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        value = other.data if isinstance(other, FakeTensor) else other
        return FakeTensor(self.data / value, self.dtype)

    def __or__(self, other):
        return FakeTensor(np.logical_or(self.data, other.data), "bool")


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


class FakeFluxPipeline:
    def __init__(self):
        self.encode_calls = 0

    def encode_prompt(self, *, prompt):
        self.encode_calls += 1
        values = [float(sum(item.encode("utf-8")) % 29) for item in prompt]
        embedding = FakeTensor(np.stack([np.full((6, 4), value) for value in values]))
        return embedding, FakeTensor(np.zeros((len(prompt), 6, 4)))


class FakeKreaPipeline:
    def __init__(self):
        self.calls: list[dict] = []
        self.encode_calls = 0

    def encode_prompt(self, *, prompt):
        self.encode_calls += 1
        values = [float(sum(item.encode("utf-8")) % 31) for item in prompt]
        embedding = FakeTensor(np.stack([np.full((6, 2, 3), value) for value in values]))
        mask = np.zeros((len(prompt), 6), dtype=bool)
        for index, item in enumerate(prompt):
            valid = min(6, max(1, len(item.split()) % 7))
            mask[index, :valid] = True
        return embedding, FakeTensor(mask, "bool")

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        value = int(float(kwargs["prompt_embeds"].data.mean()) * 7) % 255
        return SimpleNamespace(images=[Image.new("RGB", (256, 256), (value, 40, 90))])


def test_model_catalog_is_local_and_explicit() -> None:
    assert available_model_ids() == ("flux2-klein", "krea2-turbo", "procedural")
    catalog = {item["model_id"]: item for item in model_catalog()}
    assert catalog["flux2-klein"]["backend"] == "diffusers"
    assert catalog["flux2-klein"]["pipeline_class"] == "Flux2KleinPipeline"
    assert catalog["flux2-klein"]["osi_open_source"] is True
    assert catalog["krea2-turbo"]["pipeline_class"] == "Krea2Pipeline"
    assert catalog["krea2-turbo"]["open_weights"] is True
    assert catalog["krea2-turbo"]["osi_open_source"] is False
    assert catalog["krea2-turbo"]["content_filter_required"] is True


def test_codec_compiles_prompt_and_embedding_endpoints() -> None:
    codec = get_codec("krea2-turbo")
    request = codec.compile(
        base_prompt="  a ceramic wave pavilion  ",
        action=np.linspace(-1.0, 1.0, 8),
        seed=7,
        size=1024,
    )
    assert request.pipeline_class == "Krea2Pipeline"
    assert request.steps == 8
    assert request.guidance_scale == 0.0
    assert len(request.axis_prompts) == 8
    assert request.base_prompt == "a ceramic wave pavilion"
    assert "Art direction" in request.prompt


def test_flux_embedding_direction_bank_uses_prompt_embeddings() -> None:
    codec = get_codec("flux2-klein")
    request = codec.compile(
        base_prompt="an ocean observatory",
        action=np.zeros(8),
        seed=1,
        size=512,
    )
    pipeline = FakeFluxPipeline()
    bank = build_direction_bank(pipeline, request)
    kwargs = apply_direction_bank(request, bank, np.zeros(8))
    assert kwargs["prompt"] is None
    np.testing.assert_allclose(kwargs["prompt_embeds"].data, bank.base.embeddings.data)
    assert len(bank.directions) == 8
    assert pipeline.encode_calls == 1


def test_krea_renderer_uses_embedding_codec_and_validated_cache(tmp_path) -> None:
    codec = get_codec("krea2-turbo")
    renderer = LocalDiffusersRenderer(
        tmp_path,
        256,
        codec,
        device="cpu",
        dtype="float32",
        conditioning_mode="embedding",
        pipeline=(pipeline := FakeKreaPipeline()),
        torch_module=FakeTorch(),
    )

    first = renderer.render(
        design_id="same",
        seed=11,
        prompt="an impossible garden",
        action=np.zeros(8),
    )
    cached = renderer.render(
        design_id="same",
        seed=11,
        prompt="an impossible garden",
        action=np.zeros(8),
    )
    changed = renderer.render(
        design_id="same",
        seed=11,
        prompt="an impossible garden",
        action=np.full(8, 0.3),
    )

    assert first.digest == cached.digest
    assert first.request_digest == cached.request_digest
    assert changed.request_digest != first.request_digest
    assert len(pipeline.calls) == 2
    assert pipeline.encode_calls == 1
    assert pipeline.calls[0]["prompt"] is None
    assert pipeline.calls[0]["prompt_embeds_mask"].dtype == "bool"
    assert (tmp_path / "same.png.json").exists()


def test_profile_rejects_invalid_size() -> None:
    profile = get_model_profile("krea2-turbo")
    try:
        profile.validate_size(250)
    except ValueError as error:
        assert "divisible" in str(error) or "must be" in str(error)
    else:
        raise AssertionError("invalid image size was accepted")


def test_settings_selects_model_and_namespaces_runtime(monkeypatch, tmp_path) -> None:
    from art_optimizer.config import Settings

    monkeypatch.setenv("ART_OPTIMIZER_MODEL", "krea2-turbo")
    monkeypatch.setenv("ART_OPTIMIZER_DATA_DIR", str(tmp_path))
    settings = Settings.from_env()
    assert settings.model_id == "krea2-turbo"
    assert settings.renderer_size == 1024
    assert settings.data_dir == (tmp_path / "krea2-turbo").resolve()
    assert settings.database_path.parent == settings.data_dir
