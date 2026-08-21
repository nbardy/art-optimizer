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
    def encode(self, pipeline: Any, prompt: str) -> EncodedPrompt: ...

    def merge_masks(self, prompts: tuple[EncodedPrompt, ...]) -> Any | None: ...

    def pipeline_kwargs(self, encoded: EncodedPrompt) -> dict[str, Any]: ...


class Flux2ConditioningAdapter:
    def encode(self, pipeline: Any, prompt: str) -> EncodedPrompt:
        embeddings, _text_ids = pipeline.encode_prompt(prompt=prompt)
        return EncodedPrompt(embeddings=embeddings)

    def merge_masks(self, prompts: tuple[EncodedPrompt, ...]) -> None:
        return None

    def pipeline_kwargs(self, encoded: EncodedPrompt) -> dict[str, Any]:
        return {"prompt": None, "prompt_embeds": encoded.embeddings}


class Krea2ConditioningAdapter:
    def encode(self, pipeline: Any, prompt: str) -> EncodedPrompt:
        embeddings, mask = pipeline.encode_prompt(prompt=prompt)
        return EncodedPrompt(embeddings=embeddings, mask=mask)

    def merge_masks(self, prompts: tuple[EncodedPrompt, ...]) -> Any | None:
        masks = [prompt.mask for prompt in prompts if prompt.mask is not None]
        if not masks:
            return None
        merged = masks[0].clone()
        for mask in masks[1:]:
            merged = merged | mask
        return merged

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


def build_direction_bank(
    pipeline: Any,
    request: CompiledModelRequest,
) -> EmbeddingDirectionBank:
    if request.pipeline_class is None:
        raise ValueError("embedding conditioning requires a model pipeline")
    adapter = get_conditioning_adapter(request.pipeline_class)
    base = adapter.encode(pipeline, request.base_prompt)
    directions: list[Any] = []
    encoded_prompts: list[EncodedPrompt] = [base]
    for negative_prompt, positive_prompt in request.axis_prompts:
        negative = adapter.encode(pipeline, negative_prompt)
        positive = adapter.encode(pipeline, positive_prompt)
        encoded_prompts.extend((negative, positive))
        direction = (positive.embeddings - negative.embeddings) * 0.5
        directions.append(_match_rms(direction, base.embeddings))
    mask = adapter.merge_masks(tuple(encoded_prompts))
    return EmbeddingDirectionBank(
        base=EncodedPrompt(embeddings=base.embeddings, mask=mask),
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


def _match_rms(direction: Any, base: Any) -> Any:
    base_rms = base.float().square().mean().sqrt()
    direction_rms = direction.float().square().mean().sqrt().clamp_min(1e-6)
    scale = (base_rms / direction_rms).to(dtype=direction.dtype)
    return direction * scale
