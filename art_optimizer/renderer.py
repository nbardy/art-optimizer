from __future__ import annotations

import colorsys
import hashlib
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .model_codec import (
    ModelProfile,
    available_model_ids,
    get_codec,
    get_model_profile,
    selected_model_id_from_env,
)
from .rendering import (
    ImageRenderer,
    RenderedArtifact,
    RendererCapabilities,
    load_cached_artifact,
    render_request_digest,
    save_rendered_artifact,
    validate_render_input,
)


class ProceduralImageRenderer:
    """Deterministic CPU renderer for interaction and optimizer tests."""

    revision = "procedural-field/v4"
    codec_revision = "procedural-native/v1"
    control_basis_revision = "procedural-global-8d/v1"
    feature_revision = "rgb-summary-13d/v1"
    action_dimension = 8

    def __init__(self, artifacts_dir: Path, size: int = 640) -> None:
        get_model_profile("procedural").validate_size(size)
        self.profile = get_model_profile("procedural")
        self.artifacts_dir = artifacts_dir
        self.size = size
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        axis = np.linspace(-1.0, 1.0, self.size, dtype=np.float32)
        self.x, self.y = np.meshgrid(axis, axis)

    def capabilities(self) -> RendererCapabilities:
        return RendererCapabilities(
            model_id=self.profile.model_id,
            display_name=self.profile.display_name,
            model_source=self.profile.model_source,
            action_dimension=self.action_dimension,
            deterministic=True,
            supports_batching=False,
            renderer_revision=self.revision,
            codec_revision=self.codec_revision,
            control_basis_revision=self.control_basis_revision,
            feature_revision=self.feature_revision,
            replay_level="exact",
            license_id=self.profile.license_id,
            license_url=self.profile.license_url,
            open_weights=self.profile.open_weights,
            osi_open_source=self.profile.osi_open_source,
            content_filter_required=self.profile.content_filter_required,
            conditioning_mode="native",
            supports_embedding_control=False,
        )

    def render(
        self,
        *,
        design_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
    ) -> RenderedArtifact:
        action = validate_render_input(
            design_id=design_id,
            seed=seed,
            action=action,
            action_dimension=self.action_dimension,
        )
        request_payload = {
            "model_id": self.profile.model_id,
            "renderer_revision": self.revision,
            "codec_revision": self.codec_revision,
            "control_basis_revision": self.control_basis_revision,
            "prompt": " ".join(prompt.split()),
            "seed": seed,
            "action": action.astype(float).tolist(),
            "size": self.size,
        }
        request_hash = render_request_digest(request_payload)
        path = self.artifacts_dir / f"{design_id}.png"
        cached = load_cached_artifact(path, request_hash)
        if cached is not None:
            return cached

        prompt_hash = int.from_bytes(hashlib.sha256(prompt.encode("utf-8")).digest()[:8], "little")
        rng = np.random.default_rng((seed ^ prompt_hash) & ((1 << 63) - 1))

        theta = action[0] * math.pi
        ct, st = math.cos(theta), math.sin(theta)
        u = ct * self.x + st * self.y
        v = -st * self.x + ct * self.y

        frequency = 2.0 + 3.0 * (action[1] + 1.0) / 2.0
        warp_strength = 0.08 + 0.34 * (action[2] + 1.0) / 2.0
        radial_mix = (action[3] + 1.0) / 2.0
        symmetry = 2 + int(round(7 * (action[4] + 1.0) / 2.0))
        contrast = 0.85 + 2.2 * (action[5] + 1.0) / 2.0
        texture = 0.004 + 0.052 * (action[6] + 1.0) / 2.0
        openness = (action[7] + 1.0) / 2.0

        phase = rng.uniform(-math.pi, math.pi, size=8)
        center_x = rng.uniform(-0.35, 0.35) * (0.35 + 0.65 * openness)
        center_y = rng.uniform(-0.35, 0.35) * (0.35 + 0.65 * openness)
        dx = self.x - center_x
        dy = self.y - center_y
        radius = np.sqrt(dx * dx + dy * dy) + 1e-5
        angle = np.arctan2(dy, dx)

        warped_u = u + warp_strength * np.sin((2.1 + openness * 2.5) * v + phase[0])
        warped_v = v + warp_strength * np.cos((1.8 + radial_mix * 2.8) * u + phase[1])

        ribbons = np.sin(math.pi * frequency * warped_u + phase[2])
        ribbons += 0.72 * np.cos(math.pi * (frequency * 0.73 + 0.5) * warped_v + phase[3])
        spiral = np.sin(symmetry * angle + (4.0 + 7.0 * openness) * radius + phase[4])
        rings = np.cos(math.pi * (3.0 + 5.0 * radial_mix) * radius + phase[5])

        blobs = np.zeros_like(self.x)
        for _ in range(5):
            bx, by = rng.uniform(-0.85, 0.85, size=2)
            spread = rng.uniform(0.09, 0.38)
            sign = rng.choice([-1.0, 1.0])
            blobs += sign * np.exp(-((self.x - bx) ** 2 + (self.y - by) ** 2) / spread)

        field = (1.0 - radial_mix) * ribbons + radial_mix * (0.9 * spiral + 0.65 * rings)
        field += (0.25 + 0.3 * openness) * blobs
        field = np.tanh(field * contrast)

        secondary = np.sin(1.35 * field + 2.1 * warped_v + phase[6])
        tertiary = np.cos(1.8 * field - 2.6 * warped_u + phase[7])
        t = np.clip((field + 1.0) * 0.5, 0.0, 1.0)

        hue = ((prompt_hash % 360) / 360.0 + 0.19 * action[0] + 0.10 * action[3]) % 1.0
        saturation = 0.50 + 0.35 * (action[6] + 1.0) / 2.0
        lightness = 0.42 + 0.08 * action[7]
        palette = np.stack(
            [
                self._hls(hue, max(0.12, lightness - 0.18), saturation),
                self._hls(
                    (hue + 0.16 + 0.08 * action[2]) % 1.0,
                    lightness + 0.08,
                    min(0.98, saturation + 0.1),
                ),
                self._hls(
                    (hue + 0.54 + 0.06 * action[4]) % 1.0,
                    min(0.82, lightness + 0.27),
                    0.48 + 0.25 * radial_mix,
                ),
                self._hls((hue + 0.78) % 1.0, 0.16 + 0.16 * openness, 0.60),
            ],
            axis=0,
        ).astype(np.float32)

        low = np.clip(t * 3.0, 0.0, 2.999)
        segment = low.astype(np.int32)
        local = low - segment
        rgb = np.empty((*t.shape, 3), dtype=np.float32)
        for index in range(3):
            mask = segment == index
            rgb[mask] = (
                palette[index] * (1.0 - local[mask, None])
                + palette[index + 1] * local[mask, None]
            )

        glow = np.clip((secondary + 1.0) * 0.5, 0.0, 1.0)[..., None]
        rgb = rgb * (0.78 + 0.30 * glow)
        contour = np.exp(-((np.abs(np.mod(field * 4.5, 1.0) - 0.5)) / 0.065) ** 2)
        contour *= 0.12 + 0.18 * (1.0 - openness)
        rgb = rgb * (1.0 - contour[..., None]) + palette[2] * contour[..., None]

        grain = rng.normal(0.0, texture, size=rgb.shape).astype(np.float32)
        grain *= 0.45 + 0.55 * np.abs(tertiary[..., None])
        vignette = np.clip(1.08 - 0.24 * (self.x**2 + self.y**2), 0.72, 1.0)[..., None]
        rgb = np.clip(rgb * vignette + grain, 0.0, 1.0)

        image = Image.fromarray((rgb * 255.0).astype(np.uint8))
        if texture < 0.025:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.35))
        return save_rendered_artifact(
            image,
            path,
            request_digest=request_hash,
            metadata=request_payload,
        )

    @staticmethod
    def _hls(hue: float, lightness: float, saturation: float) -> np.ndarray:
        return np.asarray(colorsys.hls_to_rgb(hue, lightness, saturation), dtype=np.float32)


BackendFactory = Callable[[ModelProfile, Path, int], ImageRenderer]


def _procedural_factory(_profile: ModelProfile, artifacts_dir: Path, size: int) -> ImageRenderer:
    return ProceduralImageRenderer(artifacts_dir, size)


def _diffusers_factory(profile: ModelProfile, artifacts_dir: Path, size: int) -> ImageRenderer:
    from .diffusers_renderer import LocalDiffusersRenderer

    return LocalDiffusersRenderer(artifacts_dir, size, get_codec(profile.model_id))


_BACKENDS: dict[str, BackendFactory] = {
    "procedural": _procedural_factory,
    "diffusers": _diffusers_factory,
}


def available_renderers() -> tuple[str, ...]:
    return available_model_ids()


def build_renderer(model_id: str, artifacts_dir: Path, size: int) -> ImageRenderer:
    profile = get_model_profile(model_id)
    factory = _BACKENDS[profile.backend]
    return factory(profile, artifacts_dir, size)


class ConfiguredRenderer:
    """Compatibility facade; the registry remains the only model dispatch point."""

    def __init__(
        self,
        artifacts_dir: Path,
        size: int = 640,
        model_id: str | None = None,
    ) -> None:
        self._backend = build_renderer(
            model_id or selected_model_id_from_env(),
            artifacts_dir,
            size,
        )

    @property
    def revision(self) -> str:
        return self._backend.revision

    @property
    def codec_revision(self) -> str:
        return self._backend.codec_revision

    @property
    def control_basis_revision(self) -> str:
        return self._backend.control_basis_revision

    @property
    def feature_revision(self) -> str:
        return self._backend.feature_revision

    @property
    def action_dimension(self) -> int:
        return self._backend.action_dimension

    def capabilities(self) -> RendererCapabilities:
        return self._backend.capabilities()

    def render(
        self,
        *,
        design_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
    ) -> RenderedArtifact:
        return self._backend.render(
            design_id=design_id,
            seed=seed,
            prompt=prompt,
            action=action,
        )


ProceduralRenderer = ConfiguredRenderer
