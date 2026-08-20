from __future__ import annotations

import colorsys
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


@dataclass(slots=True)
class RenderedArtifact:
    path: Path
    feature_vector: list[float]


class ProceduralRenderer:
    """Deterministic, smooth eight-dimensional art renderer.

    This is an honest development renderer, not a diffusion-model impersonation.
    Its global control basis is deliberately smooth so the preference learner,
    streaming protocol, branching, replay, and atlas can run end to end on a CPU.
    """

    revision = "procedural-field/v1"
    control_basis_revision = "procedural-global-8d/v1"

    def __init__(self, artifacts_dir: Path, size: int = 640) -> None:
        self.artifacts_dir = artifacts_dir
        self.size = size
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        axis = np.linspace(-1.0, 1.0, self.size, dtype=np.float32)
        self.x, self.y = np.meshgrid(axis, axis)

    def render(
        self,
        *,
        design_id: str,
        seed: int,
        prompt: str,
        action: np.ndarray,
    ) -> RenderedArtifact:
        action = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        if action.shape != (8,):
            raise ValueError("procedural renderer expects exactly eight controls")

        path = self.artifacts_dir / f"{design_id}.png"
        if path.exists():
            image = Image.open(path).convert("RGB")
            array = np.asarray(image, dtype=np.float32) / 255.0
            return RenderedArtifact(path=path, feature_vector=self._features(array))

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
                self._hls((hue + 0.16 + 0.08 * action[2]) % 1.0, lightness + 0.08, min(0.98, saturation + 0.1)),
                self._hls((hue + 0.54 + 0.06 * action[4]) % 1.0, min(0.82, lightness + 0.27), 0.48 + 0.25 * radial_mix),
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
            rgb[mask] = palette[index] * (1.0 - local[mask, None]) + palette[index + 1] * local[mask, None]

        glow = np.clip((secondary + 1.0) * 0.5, 0.0, 1.0)[..., None]
        rgb = rgb * (0.78 + 0.30 * glow)
        contour = np.exp(-((np.abs(np.mod(field * 4.5, 1.0) - 0.5)) / 0.065) ** 2)
        contour *= 0.12 + 0.18 * (1.0 - openness)
        rgb = rgb * (1.0 - contour[..., None]) + palette[2] * contour[..., None]

        grain = rng.normal(0.0, texture, size=rgb.shape).astype(np.float32)
        grain *= (0.45 + 0.55 * np.abs(tertiary[..., None]))
        vignette = np.clip(1.08 - 0.24 * (self.x**2 + self.y**2), 0.72, 1.0)[..., None]
        rgb = np.clip(rgb * vignette + grain, 0.0, 1.0)

        image = Image.fromarray((rgb * 255.0).astype(np.uint8), mode="RGB")
        if texture < 0.025:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.35))
        image.save(path, format="PNG", optimize=True)
        return RenderedArtifact(path=path, feature_vector=self._features(rgb))

    @staticmethod
    def _hls(hue: float, lightness: float, saturation: float) -> np.ndarray:
        return np.asarray(colorsys.hls_to_rgb(hue, lightness, saturation), dtype=np.float32)

    @staticmethod
    def _features(rgb: np.ndarray) -> list[float]:
        rgb = np.asarray(rgb, dtype=np.float32)
        mean = rgb.mean(axis=(0, 1))
        std = rgb.std(axis=(0, 1))
        maximum = rgb.max(axis=2)
        minimum = rgb.min(axis=2)
        saturation = (maximum - minimum) / np.maximum(maximum, 1e-4)
        luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        edge_x = float(np.abs(np.diff(luminance, axis=1)).mean())
        edge_y = float(np.abs(np.diff(luminance, axis=0)).mean())
        horizontal_symmetry = float(1.0 - np.abs(rgb - rgb[:, ::-1]).mean())
        vertical_symmetry = float(1.0 - np.abs(rgb - rgb[::-1, :]).mean())
        features = np.concatenate(
            [
                mean,
                std,
                np.asarray(
                    [
                        saturation.mean(),
                        saturation.std(),
                        luminance.std(),
                        edge_x * 4.0,
                        edge_y * 4.0,
                        horizontal_symmetry,
                        vertical_symmetry,
                    ],
                    dtype=np.float32,
                ),
            ]
        )
        return np.clip(features, 0.0, 1.0).astype(float).tolist()
