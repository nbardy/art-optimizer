from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .model_codec import CompiledModelRequest


@dataclass(frozen=True, slots=True)
class EncodedPrompt:
    embeddings: Any
    mask: Any | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingDirectionBank:
    base: EncodedPrompt
    directions: tuple[Any, ...]


class ConditioningAdapter(Protocol):
    def encode(self, pipeline: Any, prompts: list[str]) -> EncodedPrompt: ...

    def output_mask(self, mask: Any | None) -> Any | None: ...

    def pipeline_kwargs(self, encoded: EncodedPrompt) -> dict[str, Any]: ...


class Flux2ConditioningAdapter:
    def encode(self, pipeline: Any, prompts: list[str]) -> EncodedPrompt:
        embeddings, _text_ids = pipeline.encode_prompt(prompt=prompts)
        return EncodedPrompt(embeddings=embeddings)

    def output_mask(self, mask: Any | None) -> None:
        return None

    def pipeline_kwargs(self, encoded: EncodedPrompt) -> dict[str, Any]:
        return {"prompt": None, "prompt_embeds": encoded.embeddings}


class Krea2ConditioningAdapter:
    def encode(self, pipeline: Any, prompts: list[str]) -> EncodedPrompt:
        embeddings, mask = pipeline.encode_prompt(prompt=prompts)
        return EncodedPrompt(embeddings=embeddings, mask=mask)

    def output_mask(self, mask: Any | None) -> Any | None:
        return None if mask is None else mask.any(dim=0, keepdim=True)

    def pipeline_kwargs(self, encoded: EncodedPrompt) -> dict[str, Any]:
        return {
            "prompt": None,
            "prompt_embeds": encoded.embeddings,
            "prompt_embeds_mask": encoded.mask,
        }


_ADAPTERS: dict[str, ConditioningAdapter] = {
    "Flux2KleinPipeline": Flux2ConditioningAdapter(),
    "Krea2Pipeline": Krea2ConditioningAdapter(),
}


def get_conditioning_adapter(pipeline_class: str) -> ConditioningAdapter:
    adapter = _ADAPTERS.get(pipeline_class)
    if adapter is None:
        available = ", ".join(sorted(_ADAPTERS))
        raise ValueError(
            f"embedding conditioning is unavailable for {pipeline_class!r}; "
            f"supported pipelines: {available}"
        )
    return adapter


def encode_base_prompt(
    pipeline: Any,
    request: CompiledModelRequest,
) -> EncodedPrompt:
    """Encode only the prompt center used by non-string embedding codecs."""

    if request.pipeline_class is None:
        raise ValueError("embedding conditioning requires a model pipeline")
    adapter = get_conditioning_adapter(request.pipeline_class)
    encoded = adapter.encode(pipeline, [request.base_prompt])
    return EncodedPrompt(
        embeddings=encoded.embeddings[0:1],
        mask=adapter.output_mask(encoded.mask),
    )


def build_direction_bank(
    pipeline: Any,
    request: CompiledModelRequest,
) -> EmbeddingDirectionBank:
    if request.pipeline_class is None:
        raise ValueError("embedding conditioning requires a model pipeline")
    adapter = get_conditioning_adapter(request.pipeline_class)
    prompts = [request.base_prompt]
    for negative_prompt, positive_prompt in request.axis_prompts:
        prompts.extend((negative_prompt, positive_prompt))
    encoded = adapter.encode(pipeline, prompts)

    base_embeddings = encoded.embeddings[0:1]
    directions = []
    for index in range(len(request.axis_prompts)):
        negative = encoded.embeddings[1 + 2 * index : 2 + 2 * index]
        positive = encoded.embeddings[2 + 2 * index : 3 + 2 * index]
        directions.append(_match_rms((positive - negative) * 0.5, base_embeddings))
    return EmbeddingDirectionBank(
        base=EncodedPrompt(
            embeddings=base_embeddings,
            mask=adapter.output_mask(encoded.mask),
        ),
        directions=tuple(directions),
    )


def apply_direction_bank(
    request: CompiledModelRequest,
    bank: EmbeddingDirectionBank,
    action: np.ndarray,
) -> dict[str, Any]:
    if request.pipeline_class is None:
        raise ValueError("embedding conditioning requires a model pipeline")
    values = np.asarray(action, dtype=np.float64)
    if values.shape != (len(bank.directions),):
        raise ValueError("embedding action dimension does not match the direction bank")
    if not np.isfinite(values).all():
        raise ValueError("embedding action must be finite")
    values = np.clip(values, -1.0, 1.0)

    mixed = bank.base.embeddings.clone()
    scale = request.embedding_strength / math.sqrt(max(len(bank.directions), 1))
    for value, direction in zip(values, bank.directions, strict=True):
        mixed = mixed + direction * (float(value) * scale)
    adapter = get_conditioning_adapter(request.pipeline_class)
    return adapter.pipeline_kwargs(EncodedPrompt(embeddings=mixed, mask=bank.base.mask))


def apply_relative_rms_offset(
    request: CompiledModelRequest,
    base: EncodedPrompt,
    offset: np.ndarray,
    torch_module: Any,
    *,
    active_mask: np.ndarray | None = None,
    base_rms: float | None = None,
) -> tuple[dict[str, Any], float]:
    """Add an offset measured in active base-embedding RMS units.

    `base_rms` is a measured scalar from the final prompt-embedding tensor, not a
    learned norm. Supplying `active_mask` prevents ignored/padded positions from
    receiving perturbation energy.
    """

    if request.pipeline_class is None:
        raise ValueError("embedding conditioning requires a model pipeline")
    expected_shape = tuple(int(item) for item in base.embeddings.shape[1:])
    values = np.asarray(offset, dtype=np.float32)
    if values.shape != expected_shape:
        raise ValueError(
            f"embedding offset shape {values.shape} does not match {expected_shape}"
        )
    if not np.isfinite(values).all():
        raise ValueError("embedding offset must be finite")

    if active_mask is not None:
        mask = np.asarray(active_mask, dtype=bool)
        if mask.shape != expected_shape:
            raise ValueError("active embedding mask does not match embedding shape")
        values = np.where(mask, values, 0.0)

    if base_rms is None:
        base_rms_tensor = base.embeddings.float().square().mean().sqrt().clamp_min(1e-6)
        measured_base_rms = float(base_rms_tensor.item())
        scale: Any = base_rms_tensor.to(dtype=base.embeddings.dtype)
    else:
        measured_base_rms = float(base_rms)
        if not math.isfinite(measured_base_rms) or measured_base_rms < 1e-6:
            raise ValueError("base embedding RMS must be finite and positive")
        scale = measured_base_rms

    tensor = torch_module.as_tensor(
        values,
        device=base.embeddings.device,
        dtype=base.embeddings.dtype,
    )
    mixed = base.embeddings + tensor.unsqueeze(0) * scale
    adapter = get_conditioning_adapter(request.pipeline_class)
    return (
        adapter.pipeline_kwargs(EncodedPrompt(embeddings=mixed, mask=base.mask)),
        measured_base_rms,
    )


def _match_rms(direction: Any, base: Any) -> Any:
    base_rms = base.float().square().mean().sqrt()
    direction_rms = direction.float().square().mean().sqrt().clamp_min(1e-6)
    scale = (base_rms / direction_rms).to(dtype=direction.dtype)
    return direction * scale
