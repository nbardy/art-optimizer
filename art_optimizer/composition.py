from __future__ import annotations

from .clean_service import CleanArtOptimizerService
from .config import Settings
from .planner import CandidatePlanner
from .renderer import build_renderer
from .rendering import ImageRenderer
from .service import ArtOptimizerService


def build_service(
    settings: Settings,
    *,
    renderer: ImageRenderer | None = None,
    planner: CandidatePlanner | None = None,
) -> ArtOptimizerService:
    """Compose the production service with the tested correctness layer."""

    selected_renderer = renderer or build_renderer(
        settings.model_id,
        settings.artifacts_dir,
        settings.renderer_size,
    )
    return CleanArtOptimizerService(
        settings,
        renderer=selected_renderer,
        planner=planner,
    )
