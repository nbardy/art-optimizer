from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class PromptAxis:
    name: str
    negative: str
    positive: str


@dataclass(frozen=True, slots=True)
class CompiledModelRequest:
    model_id: str
    model_source: str
    codec_revision: str
    control_basis_revision: str
    prompt: str
    seed: int
    width: int
    height: int
    steps: int
    guidance_scale: float


@dataclass(frozen=True, slots=True)
class SemanticPromptCodec:
    model_id: str
    model_source: str
    revision: str
    control_basis_revision: str
    steps: int
    guidance_scale: float
    axes: tuple[PromptAxis, ...]
    finish: str

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

        directives = [
            self._directive(axis, value)
            for axis, value in zip(self.axes, values, strict=True)
            if abs(float(value)) >= 0.08
        ]
        if directives:
            prompt = f"{prompt}. Art direction: {'; '.join(directives)}."
        if self.finish:
            prompt = f"{prompt} {self.finish}"

        return CompiledModelRequest(
            model_id=self.model_id,
            model_source=model_source or self.model_source,
            codec_revision=self.revision,
            control_basis_revision=self.control_basis_revision,
            prompt=prompt,
            seed=seed,
            width=size,
            height=size,
            steps=self.steps,
            guidance_scale=self.guidance_scale,
        )

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

CODECS: dict[str, SemanticPromptCodec] = {
    "flux2-klein": SemanticPromptCodec(
        model_id="flux2-klein",
        model_source="black-forest-labs/FLUX.2-klein-4B",
        revision="flux2-klein-semantic-codec/v1",
        control_basis_revision="flux2-klein-semantic-8d/v1",
        steps=4,
        guidance_scale=1.0,
        axes=_AXES,
        finish="Keep the subject coherent and produce a finished high-quality image.",
    ),
    "krea2-turbo": SemanticPromptCodec(
        model_id="krea2-turbo",
        model_source="krea/Krea-2-Turbo",
        revision="krea2-turbo-semantic-codec/v1",
        control_basis_revision="krea2-turbo-semantic-8d/v1",
        steps=8,
        guidance_scale=0.0,
        axes=_AXES,
        finish="Prioritize strong visual design, coherent art direction, and a finished image.",
    ),
}


def get_codec(codec_id: str) -> SemanticPromptCodec:
    codec = CODECS.get(codec_id)
    if codec is None:
        available = ", ".join(sorted(CODECS))
        raise ValueError(f"unknown model codec {codec_id!r}; choose one of: {available}")
    return codec
