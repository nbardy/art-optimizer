from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np

BackendKind = Literal["procedural", "diffusers"]
ConditioningMode = Literal["native", "prompt", "embedding"]


@dataclass(frozen=True, slots=True)
class PromptAxis:
    name: str
    negative: str
    positive: str


@dataclass(frozen=True, slots=True)
class ModelProfile:
    model_id: str
    display_name: str
    backend: BackendKind
    model_source: str
    pipeline_class: str | None
    codec_revision: str
    control_basis_revision: str
    action_dimension: int
    steps: int
    guidance_scale: float
    embedding_strength: float
    default_conditioning: ConditioningMode
    license_id: str
    license_url: str
    open_weights: bool
    osi_open_source: bool
    content_filter_required: bool
    commercial_use_note: str
    min_size: int
    max_size: int
    size_multiple: int
    finish: str

    def public_metadata(self) -> dict[str, object]:
        metadata = asdict(self)
        metadata.pop("finish")
        return metadata

    def validate_size(self, size: int) -> None:
        if not self.min_size <= size <= self.max_size:
            raise ValueError(
                f"{self.model_id} image size must be {self.min_size}..{self.max_size}"
            )
        if size % self.size_multiple:
            raise ValueError(
                f"{self.model_id} image size must be divisible by {self.size_multiple}"
            )


@dataclass(frozen=True, slots=True)
class CompiledModelRequest:
    model_id: str
    model_source: str
    pipeline_class: str | None
    codec_revision: str
    control_basis_revision: str
    base_prompt: str
    prompt: str
    axis_prompts: tuple[tuple[str, str], ...]
    seed: int
    width: int
    height: int
    steps: int
    guidance_scale: float
    embedding_strength: float


@dataclass(frozen=True, slots=True)
class SemanticDirectionCodec:
    profile: ModelProfile
    axes: tuple[PromptAxis, ...]

    @property
    def action_dimension(self) -> int:
        return len(self.axes)

    def compile(
        self,
        *,
        base_prompt: str,
        action: np.ndarray,
        seed: int,
        size: int,
        model_source: str | None = None,
    ) -> CompiledModelRequest:
        values = np.asarray(action, dtype=np.float64)
        if values.shape != (self.action_dimension,):
            raise ValueError(f"codec expects {self.action_dimension} controls")
        if not np.isfinite(values).all():
            raise ValueError("codec action must be finite")
        values = np.clip(values, -1.0, 1.0)
        prompt = " ".join(base_prompt.split())
        if not prompt:
            raise ValueError("base prompt cannot be blank")
        self.profile.validate_size(size)

        directives = [
            self._directive(axis, value)
            for axis, value in zip(self.axes, values, strict=True)
            if abs(float(value)) >= 0.08
        ]
        compiled_prompt = prompt
        if directives:
            compiled_prompt = f"{prompt}. Art direction: {'; '.join(directives)}."
        if self.profile.finish:
            compiled_prompt = f"{compiled_prompt} {self.profile.finish}"

        axis_prompts = tuple(
            (
                self._endpoint_prompt(prompt, axis.negative),
                self._endpoint_prompt(prompt, axis.positive),
            )
            for axis in self.axes
        )
        return CompiledModelRequest(
            model_id=self.profile.model_id,
            model_source=model_source or self.profile.model_source,
            pipeline_class=self.profile.pipeline_class,
            codec_revision=self.profile.codec_revision,
            control_basis_revision=self.profile.control_basis_revision,
            base_prompt=prompt,
            prompt=compiled_prompt,
            axis_prompts=axis_prompts,
            seed=seed,
            width=size,
            height=size,
            steps=self.profile.steps,
            guidance_scale=self.profile.guidance_scale,
            embedding_strength=self.profile.embedding_strength,
        )

    def _endpoint_prompt(self, base_prompt: str, phrase: str) -> str:
        prompt = f"{base_prompt}. Art direction: strongly {phrase}."
        if self.profile.finish:
            prompt = f"{prompt} {self.profile.finish}"
        return prompt

    @staticmethod
    def _directive(axis: PromptAxis, value: float) -> str:
        magnitude = abs(float(value))
        adverb = next(label for threshold, label in _STRENGTHS if magnitude >= threshold)
        phrase = axis.positive if value >= 0 else axis.negative
        return f"{adverb} {phrase}"


_STRENGTHS = ((0.72, "strongly"), (0.35, "clearly"), (0.0, "slightly"))
_AXES = (
    PromptAxis("composition", "an intimate close-up composition", "an expansive wide composition"),
    PromptAxis("form", "organic flowing forms", "precise geometric forms"),
    PromptAxis("palette", "a cool restrained palette", "a warm saturated palette"),
    PromptAxis("lighting", "soft diffuse lighting", "dramatic directional lighting"),
    PromptAxis("detail", "minimal visual detail", "dense intricate visual detail"),
    PromptAxis("material", "matte painterly surfaces", "glossy translucent surfaces"),
    PromptAxis("motion", "still orderly energy", "dynamic turbulent motion"),
    PromptAxis("realism", "abstract stylized rendering", "materially realistic rendering"),
)

_PROFILES: dict[str, ModelProfile] = {
    "procedural": ModelProfile(
        model_id="procedural",
        display_name="Procedural reference renderer",
        backend="procedural",
        model_source="builtin",
        pipeline_class=None,
        codec_revision="procedural-native/v1",
        control_basis_revision="procedural-global-8d/v1",
        action_dimension=8,
        steps=0,
        guidance_scale=0.0,
        embedding_strength=0.0,
        default_conditioning="native",
        license_id="MIT",
        license_url="https://github.com/nbardy/art-optimizer/blob/main/LICENSE",
        open_weights=True,
        osi_open_source=True,
        content_filter_required=False,
        commercial_use_note="Covered by the repository MIT license.",
        min_size=64,
        max_size=2048,
        size_multiple=1,
        finish="",
    ),
    "flux2-klein": ModelProfile(
        model_id="flux2-klein",
        display_name="FLUX.2 Klein 4B",
        backend="diffusers",
        model_source="black-forest-labs/FLUX.2-klein-4B",
        pipeline_class="Flux2KleinPipeline",
        codec_revision="flux2-klein-embedding-codec/v2",
        control_basis_revision="flux2-klein-semantic-embedding-8d/v1",
        action_dimension=8,
        steps=4,
        guidance_scale=1.0,
        embedding_strength=0.24,
        default_conditioning="embedding",
        license_id="Apache-2.0",
        license_url="https://huggingface.co/black-forest-labs/FLUX.2-klein-4B",
        open_weights=True,
        osi_open_source=True,
        content_filter_required=False,
        commercial_use_note="Apache-2.0 model weights.",
        min_size=256,
        max_size=2048,
        size_multiple=16,
        finish="Keep the subject coherent and produce a finished high-quality image.",
    ),
    "krea2-turbo": ModelProfile(
        model_id="krea2-turbo",
        display_name="Krea 2 Turbo",
        backend="diffusers",
        model_source="krea/Krea-2-Turbo",
        pipeline_class="Krea2Pipeline",
        codec_revision="krea2-turbo-embedding-codec/v2",
        control_basis_revision="krea2-turbo-semantic-embedding-8d/v1",
        action_dimension=8,
        steps=8,
        guidance_scale=0.0,
        embedding_strength=0.18,
        default_conditioning="embedding",
        license_id="Krea-2-Community",
        license_url="https://www.krea.ai/krea-2-licensing",
        open_weights=True,
        osi_open_source=False,
        content_filter_required=True,
        commercial_use_note=(
            "Community terms permit commercial use below $1M company-wide trailing annual "
            "revenue; an enterprise license is required above that threshold."
        ),
        min_size=256,
        max_size=2048,
        size_multiple=16,
        finish="Prioritize strong visual design, coherent art direction, and a finished image.",
    ),
}
_CODECS = {
    model_id: SemanticDirectionCodec(profile=profile, axes=_AXES)
    for model_id, profile in _PROFILES.items()
}


def available_model_ids() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES))


def get_model_profile(model_id: str) -> ModelProfile:
    profile = _PROFILES.get(model_id)
    if profile is None:
        available = ", ".join(available_model_ids())
        raise ValueError(f"unknown model {model_id!r}; choose one of: {available}")
    return profile


def get_codec(model_id: str) -> SemanticDirectionCodec:
    codec = _CODECS.get(model_id)
    if codec is None:
        available = ", ".join(available_model_ids())
        raise ValueError(f"unknown model codec {model_id!r}; choose one of: {available}")
    return codec


def model_catalog() -> list[dict[str, object]]:
    return [get_model_profile(model_id).public_metadata() for model_id in available_model_ids()]


def selected_model_id_from_env() -> str:
    return os.environ.get(
        "ART_OPTIMIZER_MODEL",
        os.environ.get("ART_OPTIMIZER_RENDERER", "procedural"),
    ).strip().lower()
