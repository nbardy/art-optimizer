from __future__ import annotations

import asyncio

from .atlas import PersistentPreferenceAtlas
from .config import Settings
from .event_store import EventStore
from .planner import CandidatePlanner
from .renderer import build_renderer
from .rendering import ImageRenderer
from .service import ArtOptimizerService


class ConfiguredArtOptimizerService(ArtOptimizerService):
    """Explicit process composition root for swappable renderers and planners."""

    def __init__(
        self,
        settings: Settings,
        *,
        renderer: ImageRenderer | None = None,
        planner: CandidatePlanner | None = None,
    ) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self.store = EventStore(settings.database_path)
        self.renderer = renderer or build_renderer(
            settings.model_id,
            settings.artifacts_dir,
            settings.renderer_size,
        )
        capabilities = self.renderer.capabilities()
        if capabilities.action_dimension != settings.action_dimension:
            raise ValueError("renderer and configured action dimensions do not match")
        self.planner = planner or CandidatePlanner(capabilities.action_dimension)
        self.atlas = PersistentPreferenceAtlas(self.store.load_atlas())
        self._atlas_lock = asyncio.Lock()
        self._runtime_load_lock = asyncio.Lock()
        self._sessions = {}
