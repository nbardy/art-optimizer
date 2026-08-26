from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from .domain import MAX_SEED
from .random_embedding_codec import (
    EmbeddingPathStep,
    RandomEmbeddingCodecId,
    embedding_walk_digest,
    get_random_embedding_codec,
    random_embedding_codec_catalog,
)
from .service import ConflictError
from .taste_contracts import ContractModel


class DirectionPathStep(ContractModel):
    codec_id: RandomEmbeddingCodecId
    point_seed: int = Field(ge=0, le=MAX_SEED)
    candidate_index: int = Field(ge=0, le=3)
    radius: float = Field(gt=0.0, le=1.5)

    def as_step(self) -> EmbeddingPathStep:
        return EmbeddingPathStep(
            codec_id=self.codec_id,
            point_seed=self.point_seed,
            candidate_index=self.candidate_index,
            radius=self.radius,
        )


class DirectionSlateRequest(ContractModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    image_seed: int = Field(ge=0, le=MAX_SEED)
    point_seed: int = Field(ge=0, le=MAX_SEED)
    codec_id: RandomEmbeddingCodecId = "orthogonal-shell"
    radius: float = Field(default=0.40, gt=0.0, le=1.5)
    center_path: list[DirectionPathStep] = Field(default_factory=list, max_length=24)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("prompt cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_codec_radius(self) -> Self:
        profile = get_random_embedding_codec(self.codec_id)
        if not profile.minimum_radius <= self.radius <= profile.maximum_radius:
            raise ValueError(
                f"{self.codec_id} radius must lie in "
                f"[{profile.minimum_radius}, {profile.maximum_radius}]"
            )
        total_radius = sum(item.radius for item in self.center_path)
        if total_radius > 8.0:
            raise ValueError("embedding walk is too long; step back or reset the center")
        return self


@dataclass(slots=True)
class DirectionLabService:
    renderer: Any

    def catalog(self) -> list[dict[str, object]]:
        return random_embedding_codec_catalog()

    async def generate(self, request: DirectionSlateRequest) -> dict[str, object]:
        capabilities = self.renderer.capabilities()
        if not capabilities.supports_embedding_control:
            raise ConflictError(
                "Random embedding codecs require a Diffusers model running in embedding mode. "
                "Start FLUX.2 Klein or Krea 2 Turbo, then reopen Direction Lab."
            )
        if capabilities.conditioning_mode != "embedding":
            raise ConflictError(
                "Direction Lab requires embedding conditioning; prompt-string conditioning "
                "cannot execute non-string random points."
            )

        steps = [item.as_step() for item in request.center_path]
        digest = embedding_walk_digest(
            prompt=request.prompt,
            image_seed=request.image_seed,
            codec_id=request.codec_id,
            point_seed=request.point_seed,
            radius=request.radius,
            center_steps=steps,
        )
        slate_id = f"direction_slate_{digest[:24]}"
        design_ids = [f"direction_{digest[:24]}_{index + 1}" for index in range(4)]
        try:
            rendered = await asyncio.to_thread(
                self.renderer.render_embedding_slate,
                design_ids=design_ids,
                image_seed=request.image_seed,
                prompt=request.prompt,
                codec_id=request.codec_id,
                point_seed=request.point_seed,
                radius=request.radius,
                center_steps=steps,
            )
        except (TypeError, AttributeError, NotImplementedError) as error:
            raise ConflictError(
                "The active renderer does not implement random embedding slates."
            ) from error

        profile = get_random_embedding_codec(request.codec_id)
        artifacts = rendered["artifacts"]
        offsets = rendered["candidate_offsets"]
        cells = []
        for index, (design_id, artifact, offset_rms) in enumerate(
            zip(design_ids, artifacts, offsets, strict=True)
        ):
            cells.append(
                {
                    "candidate_index": index,
                    "design_id": design_id,
                    "image_url": f"/assets/{design_id}.png",
                    "image_digest": artifact.digest,
                    "offset_rms_relative_to_base": float(offset_rms),
                    "step": {
                        "codec_id": request.codec_id,
                        "point_seed": request.point_seed,
                        "candidate_index": index,
                        "radius": request.radius,
                    },
                }
            )

        return {
            "schema": "direction-lab-slate/v1",
            "slate_id": slate_id,
            "codec": profile.public_metadata(),
            "model_id": capabilities.model_id,
            "renderer_revision": capabilities.renderer_revision,
            "codec_revision": capabilities.codec_revision,
            "prompt": request.prompt,
            "image_seed": request.image_seed,
            "point_seed": request.point_seed,
            "radius": request.radius,
            "center_path": [item.model_dump(mode="json") for item in request.center_path],
            "center_depth": len(request.center_path),
            "fixed_image_seed": True,
            "string_axes_used": False,
            "diagnostics": rendered["diagnostics"],
            "cells": cells,
        }
