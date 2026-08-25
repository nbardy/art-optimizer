from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np

from .domain import BranchNode, SearchState, SessionState, WorldState, new_id
from .gallery_contracts import TasteGalleryCell, TasteGalleryManifest
from .preference import BayesianChoiceModel
from .rendering import RenderedArtifact
from .service import ArtOptimizerService, SessionRuntime


async def create_session_from_cell(
    service: ArtOptimizerService,
    *,
    new_session_id: str,
    source_snapshot: dict[str, Any],
    manifest: TasteGalleryManifest,
    cell: TasteGalleryCell,
) -> None:
    """Create one clean fixed-root session from an immutable gallery cell."""

    path = Path(cell.image_path)
    if path.exists():
        artifact = RenderedArtifact(
            path=path,
            feature_vector=cell.feature_vector,
            digest=cell.image_digest,
        )
    else:
        artifact = await asyncio.to_thread(
            service.renderer.render,
            design_id=cell.design_id,
            seed=cell.seed,
            prompt=manifest.prompt,
            action=np.asarray(cell.action, dtype=np.float64),
        )

    world_id = new_id("world")
    root_design = service._design_from_artifact(
        design_id=cell.design_id,
        world_id=world_id,
        seed=cell.seed,
        prompt=manifest.prompt,
        action=np.asarray(cell.action, dtype=np.float64),
        artifact=artifact,
    )
    model = BayesianChoiceModel(service.settings.action_dimension)
    search_state = SearchState()
    branch = BranchNode(
        branch_node_id=new_id("branch"),
        design_id=root_design.design_id,
        posterior=model.snapshot(),
        search_state=search_state.model_copy(deep=True),
    )
    world = WorldState(
        world_id=world_id,
        seed=cell.seed,
        prompt=manifest.prompt,
        root_design_id=root_design.design_id,
        renderer_revision=service.renderer.revision,
        control_basis_revision=service.renderer.control_basis_revision,
        initialization_mode="composition",
        initialization_action=cell.action,
    )
    state = SessionState(
        session_id=new_session_id,
        prompt=manifest.prompt,
        world=world,
        worlds={world_id: world},
        designs={root_design.design_id: root_design},
        branches={branch.branch_node_id: branch},
        current_design_id=root_design.design_id,
        current_branch_node_id=branch.branch_node_id,
        active_posterior=model.snapshot(),
        search_state=search_state,
        history=[branch.branch_node_id],
    )
    runtime = SessionRuntime(state=state)
    service._sessions[new_session_id] = runtime
    service.store.record_session_event(
        state,
        "world_created",
        {
            "world_id": world_id,
            "root_design_id": root_design.design_id,
            "seed": cell.seed,
            "prompt": manifest.prompt,
            "mode": "composition",
            "initial_action": cell.action,
            "source_gallery_id": manifest.gallery_id,
            "source_taste_id": manifest.taste_id,
            "source_session_id": source_snapshot["session_id"],
            "renderer_revision": service.renderer.revision,
            "control_basis_revision": service.renderer.control_basis_revision,
        },
    )
    await service._start_round(runtime)
