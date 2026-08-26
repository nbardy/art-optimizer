from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .embedding_conditioning import (
    EmbeddingDirectionBank,
    EncodedPrompt,
    apply_direction_bank,
    apply_relative_rms_offset,
    build_direction_bank,
    encode_base_prompt,
)
from .embedding_metric import (
    RMS_METRIC_REVISION,
    active_candidate_offsets,
    active_embedding_metric,
)
from .model_codec import SemanticDirectionCodec
from .random_embedding_codec import EmbeddingPathStep, get_random_embedding_codec
from .rendering import (
    RenderedArtifact,
    RendererCapabilities,
    load_cached_artifact,
    render_request_digest,
    save_rendered_artifact,
    validate_render_input,
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_DTYPE_NAMES = frozenset({"bfloat16", "float16", "float32"})
_CONDITIONING_MODES = frozenset({"prompt", "embedding"})


class LocalDiffusersRenderer:
    """Lazy local open-weight renderer driven by one model profile and codec."""

    feature_revision = "rgb-summary-13d/v1"

    def __init__(
        self,
        artifacts_dir: Path,
        size: int,
        codec: SemanticDirectionCodec,
        *,
        model_source: str | None = None,
        device: str | None = None,
        dtype: str | None = None,
        cpu_offload: bool | None = None,
        local_files_only: bool | None = None,
        conditioning_mode: str | None = None,
        pipeline: Any | None = None,
        torch_module: Any | None = None,
    ) -> None:
        codec.profile.validate_size(size)
        if codec.profile.pipeline_class is None:
            raise ValueError("a local Diffusers renderer requires a pipeline class")
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.size = size
        self.codec = codec
        self.profile = codec.profile
        self.model_source = model_source or os.environ.get(
            "ART_OPTIMIZER_MODEL_SOURCE", self.profile.model_source
        )
        self.model_revision = os.environ.get("ART_OPTIMIZER_MODEL_REVISION") or None
        self.diffusers_version = _package_version("diffusers")
        self.torch_version = _package_version("torch")
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
        self.conditioning_mode = (
            conditioning_mode
            or os.environ.get(
                "ART_OPTIMIZER_CONDITIONING_MODE",
                self.profile.default_conditioning,
            )
        ).strip().lower()
        if self.conditioning_mode not in _CONDITIONING_MODES:
            raise ValueError(
                f"unsupported conditioning mode {self.conditioning_mode!r}; "
                "choose prompt or embedding"
            )
        self.action_dimension = codec.action_dimension
        self.revision = f"local-diffusers/{self.profile.model_id}/v4"
        self.codec_revision = codec.profile.codec_revision
        self.control_basis_revision = codec.profile.control_basis_revision
        if (pipeline is None) != (torch_module is None):
            raise ValueError("pipeline and torch_module must be supplied together")
        if pipeline is None:
            _require_dependencies()
        self._pipeline = pipeline
        self._torch = torch_module
        self._lock = threading.Lock()
        self._bank_cache: OrderedDict[str, EmbeddingDirectionBank] = OrderedDict()
        self._bank_cache_size = 2
        self._base_cache: OrderedDict[str, EncodedPrompt] = OrderedDict()
        self._base_cache_size = 4

    def capabilities(self) -> RendererCapabilities:
        return RendererCapabilities(
            model_id=self.profile.model_id,
            display_name=self.profile.display_name,
            model_source=self.model_source,
            action_dimension=self.action_dimension,
            deterministic=False,
            supports_batching=False,
            renderer_revision=self.revision,
            codec_revision=self.codec_revision,
            control_basis_revision=self.control_basis_revision,
            feature_revision=self.feature_revision,
            replay_level="best_effort",
            license_id=self.profile.license_id,
            license_url=self.profile.license_url,
            open_weights=self.profile.open_weights,
            osi_open_source=self.profile.osi_open_source,
            content_filter_required=self.profile.content_filter_required,
            conditioning_mode=self.conditioning_mode,
            supports_embedding_control=True,
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
        request = self.codec.compile(
            base_prompt=prompt,
            action=values,
            seed=seed,
            size=self.size,
            model_source=self.model_source,
        )
        request_payload = {
            "model_id": request.model_id,
            "model_source": request.model_source,
            "pipeline_class": request.pipeline_class,
            "renderer_revision": self.revision,
            "codec_revision": request.codec_revision,
            "control_basis_revision": request.control_basis_revision,
            "conditioning_mode": self.conditioning_mode,
            "embedding_strength": request.embedding_strength,
            "model_revision": self.model_revision,
            "diffusers_version": self.diffusers_version,
            "torch_version": self.torch_version,
            "prompt": request.base_prompt,
            "action": values.astype(float).tolist(),
            "seed": request.seed,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "guidance_scale": request.guidance_scale,
            "dtype": self.dtype,
        }
        request_hash = render_request_digest(request_payload)
        path = self.artifacts_dir / f"{design_id}.png"
        cached = load_cached_artifact(path, request_hash)
        if cached is not None:
            return cached

        with self._lock:
            pipeline, torch = self._load_pipeline()
            generator = self._generator(torch, request.seed)
            with torch.inference_mode():
                if self.conditioning_mode == "embedding":
                    conditioning = self._embedding_kwargs(pipeline, request, values)
                else:
                    conditioning = {"prompt": request.prompt}
                output = pipeline(
                    **conditioning,
                    height=request.height,
                    width=request.width,
                    num_inference_steps=request.steps,
                    guidance_scale=request.guidance_scale,
                    generator=generator,
                )
        image = output.images[0].convert("RGB")
        return save_rendered_artifact(
            image,
            path,
            request_digest=request_hash,
            metadata=request_payload,
        )

    def render_embedding_slate(
        self,
        *,
        design_ids: Sequence[str],
        image_seed: int,
        prompt: str,
        codec_id: str,
        point_seed: int,
        radius: float,
        center_steps: Sequence[EmbeddingPathStep],
    ) -> dict[str, object]:
        """Render four non-string points on an active-token RMS shell."""

        if self.conditioning_mode != "embedding":
            raise NotImplementedError(
                "random embedding slates require embedding conditioning"
            )
        if len(design_ids) != 4 or len(set(design_ids)) != 4:
            raise ValueError("random embedding slates require four unique design IDs")
        profile = get_random_embedding_codec(codec_id)
        request = self.codec.compile(
            base_prompt=prompt,
            action=np.zeros(self.action_dimension, dtype=np.float64),
            seed=image_seed,
            size=self.size,
            model_source=self.model_source,
        )

        with self._lock:
            pipeline, torch = self._load_pipeline()
            base = self._base_prompt(pipeline, request)
            embedding_shape = tuple(int(item) for item in base.embeddings.shape[1:])
            active_mask, base_rms = active_embedding_metric(base)
            offsets, diagnostics = active_candidate_offsets(
                embedding_shape,
                codec_id=codec_id,
                point_seed=point_seed,
                radius=radius,
                center_steps=center_steps,
                active_mask=active_mask,
            )
            artifacts: list[RenderedArtifact] = []
            candidate_rms = diagnostics["candidate_offset_rms_relative_to_base"]
            for index, (design_id, offset) in enumerate(
                zip(design_ids, offsets, strict=True)
            ):
                validate_render_input(
                    design_id=design_id,
                    seed=image_seed,
                    action=np.zeros(self.action_dimension),
                    action_dimension=self.action_dimension,
                )
                offset32 = np.asarray(offset, dtype="<f4")
                offset_digest = hashlib.sha256(offset32.tobytes()).hexdigest()
                request_payload = {
                    "schema": "random-embedding-render/v2",
                    "model_id": request.model_id,
                    "model_source": request.model_source,
                    "pipeline_class": request.pipeline_class,
                    "renderer_revision": self.revision,
                    "codec_revision": request.codec_revision,
                    "conditioning_mode": "embedding",
                    "random_embedding_codec": profile.codec_id,
                    "random_embedding_codec_revision": profile.revision,
                    "rms_metric": RMS_METRIC_REVISION,
                    "active_embedding_elements": diagnostics["active_embedding_elements"],
                    "total_embedding_elements": diagnostics["total_embedding_elements"],
                    "point_seed": point_seed,
                    "candidate_index": index,
                    "radius_relative_to_base_rms": float(radius),
                    "candidate_offset_rms_relative_to_base": float(candidate_rms[index]),
                    "center_steps": [step.public_metadata() for step in center_steps],
                    "offset_digest": offset_digest,
                    "base_embedding_rms": base_rms,
                    "model_revision": self.model_revision,
                    "diffusers_version": self.diffusers_version,
                    "torch_version": self.torch_version,
                    "prompt": request.base_prompt,
                    "image_seed": image_seed,
                    "width": request.width,
                    "height": request.height,
                    "steps": request.steps,
                    "guidance_scale": request.guidance_scale,
                    "dtype": self.dtype,
                }
                request_hash = render_request_digest(request_payload)
                path = self.artifacts_dir / f"{design_id}.png"
                cached = load_cached_artifact(path, request_hash)
                if cached is not None:
                    artifacts.append(cached)
                    continue

                conditioning, measured_base_rms = apply_relative_rms_offset(
                    request,
                    base,
                    offset,
                    torch,
                    active_mask=active_mask,
                    base_rms=base_rms,
                )
                if not np.isclose(measured_base_rms, base_rms, rtol=1e-6, atol=1e-8):
                    raise RuntimeError("base embedding RMS changed during one slate")
                generator = self._generator(torch, image_seed)
                with torch.inference_mode():
                    output = pipeline(
                        **conditioning,
                        height=request.height,
                        width=request.width,
                        num_inference_steps=request.steps,
                        guidance_scale=request.guidance_scale,
                        generator=generator,
                    )
                image = output.images[0].convert("RGB")
                artifacts.append(
                    save_rendered_artifact(
                        image,
                        path,
                        request_digest=request_hash,
                        metadata=request_payload,
                    )
                )

        return {
            "artifacts": artifacts,
            "candidate_offsets": candidate_rms,
            "diagnostics": {
                **diagnostics,
                "embedding_shape": list(embedding_shape),
                "base_embedding_rms": base_rms,
                "all_candidates_share_image_seed": True,
                "string_axes_used": False,
            },
        }

    def _embedding_kwargs(
        self,
        pipeline: Any,
        request: Any,
        action: np.ndarray,
    ) -> dict[str, Any]:
        key = hashlib.sha256(
            (
                f"{request.model_source}\0{request.codec_revision}\0"
                f"{request.base_prompt}"
            ).encode("utf-8")
        ).hexdigest()
        bank = self._bank_cache.get(key)
        if bank is None:
            bank = build_direction_bank(pipeline, request)
            self._bank_cache[key] = bank
            self._bank_cache.move_to_end(key)
            while len(self._bank_cache) > self._bank_cache_size:
                self._bank_cache.popitem(last=False)
        else:
            self._bank_cache.move_to_end(key)
        return apply_direction_bank(request, bank, action)

    def _base_prompt(self, pipeline: Any, request: Any) -> EncodedPrompt:
        key = hashlib.sha256(
            (
                f"{request.model_source}\0{self.model_revision}\0"
                f"{request.codec_revision}\0{request.base_prompt}"
            ).encode("utf-8")
        ).hexdigest()
        encoded = self._base_cache.get(key)
        if encoded is None:
            encoded = encode_base_prompt(pipeline, request)
            self._base_cache[key] = encoded
            self._base_cache.move_to_end(key)
            while len(self._base_cache) > self._base_cache_size:
                self._base_cache.popitem(last=False)
        else:
            self._base_cache.move_to_end(key)
        return encoded

    def _generator(self, torch: Any, seed: int) -> Any:
        generator_device = "cpu" if self.cpu_offload or self.device == "mps" else self.device
        return torch.Generator(device=generator_device).manual_seed(seed)

    def _load_pipeline(self) -> tuple[Any, Any]:
        if self._pipeline is not None and self._torch is not None:
            return self._pipeline, self._torch
        _require_dependencies()
        torch = importlib.import_module("torch")
        diffusers = importlib.import_module("diffusers")
        pipeline_class = getattr(diffusers, self.profile.pipeline_class, None)
        if pipeline_class is None:
            raise RuntimeError(
                f"installed Diffusers does not provide {self.profile.pipeline_class}; "
                "upgrade the models extra"
            )
        torch_dtype = getattr(torch, self.dtype)
        load_kwargs: dict[str, Any] = {
            "torch_dtype": torch_dtype,
            "local_files_only": self.local_files_only,
            "trust_remote_code": False,
        }
        if self.model_revision:
            load_kwargs["revision"] = self.model_revision
        token = os.environ.get("HF_TOKEN")
        if token:
            load_kwargs["token"] = token
        pipeline = pipeline_class.from_pretrained(self.model_source, **load_kwargs)
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


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _require_dependencies() -> None:
    missing = [
        name for name in ("torch", "diffusers") if importlib.util.find_spec(name) is None
    ]
    if missing:
        packages = ", ".join(missing)
        raise RuntimeError(
            f"local model dependencies are missing ({packages}); "
            "install art-optimizer[models]"
        )
