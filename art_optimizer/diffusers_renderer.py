from __future__ import annotations

import importlib
import importlib.util
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .model_codec import SemanticPromptCodec
from .rendering import (
    RenderedArtifact,
    RendererCapabilities,
    atomic_save_png,
    file_digest,
    image_features,
    validate_render_input,
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_DTYPE_NAMES = frozenset({"bfloat16", "float16", "float32"})


class LocalDiffusersRenderer:
    """Lazy local Diffusers renderer driven by a model codec."""

    feature_revision = "rgb-summary-13d/v1"

    def __init__(
        self,
        artifacts_dir: Path,
        size: int,
        codec: SemanticPromptCodec,
        *,
        model_source: str | None = None,
        device: str | None = None,
        dtype: str | None = None,
        cpu_offload: bool | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        if not 256 <= size <= 2048 or size % 16:
            raise ValueError("local model image size must be 256..2048 and divisible by 16")
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.size = size
        self.codec = codec
        self.model_source = model_source or os.environ.get(
            "ART_OPTIMIZER_MODEL_SOURCE", codec.model_source
        )
        self.device = device or os.environ.get("ART_OPTIMIZER_DEVICE", "cuda")
        self.dtype = dtype or os.environ.get("ART_OPTIMIZER_DTYPE", "bfloat16")
        if self.dtype not in _DTYPE_NAMES:
            raise ValueError(f"unsupported dtype: {self.dtype}")
        self.cpu_offload = (
            _env_flag("ART_OPTIMIZER_CPU_OFFLOAD", False)
            if cpu_offload is None
            else cpu_offload
        )
        self.local_files_only = (
            _env_flag("ART_OPTIMIZER_LOCAL_FILES_ONLY", False)
            if local_files_only is None
            else local_files_only
        )
        self.action_dimension = codec.action_dimension
        self.revision = f"local-diffusers/{codec.model_id}/v1"
        self.codec_revision = codec.revision
        self.control_basis_revision = codec.control_basis_revision
        self._pipeline: Any | None = None
        self._torch: Any | None = None
        self._lock = threading.Lock()

    def capabilities(self) -> RendererCapabilities:
        return RendererCapabilities(
            model_id=self.codec.model_id,
            action_dimension=self.action_dimension,
            deterministic=False,
            supports_batching=False,
            renderer_revision=self.revision,
            codec_revision=self.codec_revision,
            control_basis_revision=self.control_basis_revision,
            feature_revision=self.feature_revision,
            replay_level="best_effort",
        )

    def render(
        self,
        *,
        design_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
    ) -> RenderedArtifact:
        values = validate_render_input(
            design_id=design_id,
            seed=seed,
            action=action,
            action_dimension=self.action_dimension,
        )
        path = self.artifacts_dir / f"{design_id}.png"
        if path.exists():
            with Image.open(path) as stored:
                image = stored.convert("RGB")
                features = image_features(image)
            return RenderedArtifact(path=path, feature_vector=features, digest=file_digest(path))

        request = self.codec.compile(
            base_prompt=prompt,
            action=values,
            seed=seed,
            size=self.size,
            model_source=self.model_source,
        )
        with self._lock:
            pipeline, torch = self._load_pipeline()
            generator_device = "cpu" if self.cpu_offload or self.device == "mps" else self.device
            generator = torch.Generator(device=generator_device).manual_seed(request.seed)
            with torch.inference_mode():
                output = pipeline(
                    prompt=request.prompt,
                    height=request.height,
                    width=request.width,
                    num_inference_steps=request.steps,
                    guidance_scale=request.guidance_scale,
                    generator=generator,
                )
        image = output.images[0].convert("RGB")
        atomic_save_png(image, path)
        return RenderedArtifact(
            path=path,
            feature_vector=image_features(image),
            digest=file_digest(path),
        )

    def _load_pipeline(self) -> tuple[Any, Any]:
        if self._pipeline is not None and self._torch is not None:
            return self._pipeline, self._torch
        missing = [name for name in ("torch", "diffusers") if importlib.util.find_spec(name) is None]
        if missing:
            packages = ", ".join(missing)
            raise RuntimeError(
                f"local model dependencies are missing ({packages}); install art-optimizer[models]"
            )
        torch = importlib.import_module("torch")
        diffusers = importlib.import_module("diffusers")
        torch_dtype = getattr(torch, self.dtype)
        pipeline = diffusers.DiffusionPipeline.from_pretrained(
            self.model_source,
            torch_dtype=torch_dtype,
            local_files_only=self.local_files_only,
        )
        if self.cpu_offload:
            pipeline.enable_model_cpu_offload()
        else:
            pipeline.to(self.device)
        self._pipeline = pipeline
        self._torch = torch
        return pipeline, torch


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in _TRUE_VALUES
