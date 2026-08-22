from __future__ import annotations

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
    """Compose one service state machine with replaceable renderer/planner seams."""

    selected_renderer = renderer or build_renderer(
        settings.model_id,
        settings.artifacts_dir,
        settings.renderer_size,
    )
    return ArtOptimizerService(
        settings,
        renderer=selected_renderer,
        planner=planner,
    )
