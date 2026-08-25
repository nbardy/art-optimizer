from __future__ import annotations

import asyncio

import numpy as np

from .rendering import RenderedArtifact, artifact_manifest_path
from .service import ArtOptimizerService, OperationError


class BoundedGalleryRenderer:
    """Render gallery cells with bounded concurrency and all-or-clean failure."""

    def __init__(self, service: ArtOptimizerService, concurrency: int = 2) -> None:
        if concurrency < 1:
            raise ValueError("gallery render concurrency must be positive")
        self.service = service
        self._slots = asyncio.Semaphore(concurrency)

    async def render(
        self,
        prompt: str,
        specs: list[dict[str, object]],
    ) -> list[RenderedArtifact]:
        async def render_one(spec: dict[str, object]) -> RenderedArtifact:
            async with self._slots:
                return await asyncio.to_thread(
                    self.service.renderer.render,
                    design_id=str(spec["design_id"]),
                    seed=int(spec["seed"]),
                    prompt=prompt,
                    action=np.asarray(spec["action"], dtype=np.float64),
                )

        results = await asyncio.gather(
            *(render_one(spec) for spec in specs),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            for spec, result in zip(specs, results, strict=True):
                if isinstance(result, RenderedArtifact) and not bool(spec["preexisting"]):
                    result.path.unlink(missing_ok=True)
                    artifact_manifest_path(result.path).unlink(missing_ok=True)
            messages = "; ".join(str(error) for error in failures[:3])
            raise OperationError(f"taste gallery rendering failed: {messages}")
        return [result for result in results if isinstance(result, RenderedArtifact)]
