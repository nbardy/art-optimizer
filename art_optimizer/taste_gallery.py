from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .domain import CommandPayload, utc_now
from .emergent_experiment import EmergentTasteExperiment
from .gallery_contracts import (
    GALLERY_ACTIVATED_EVENT_KIND,
    GALLERY_EVENT_KIND,
    GALLERY_SESSION_EVENT_KIND,
    TasteGalleryActivationPayload,
    TasteGalleryCell,
    TasteGalleryManifest,
    TasteGalleryRequest,
    cell_specs,
    gallery_id,
    gallery_seeds,
    gallery_session_id,
    public_gallery,
    representation_scope,
)
from .gallery_render import BoundedGalleryRenderer
from .gallery_session import create_session_from_cell
from .service import ArtOptimizerService, ConflictError, NotFoundError

__all__ = [
    "TasteGalleryActivationPayload",
    "TasteGalleryCell",
    "TasteGalleryManifest",
    "TasteGalleryRequest",
    "TasteGalleryService",
]


@dataclass(slots=True)
class TasteGalleryService:
    """Bounded, read-only seed-by-strength inspection of one taste center."""

    service: ArtOptimizerService
    emergent: EmergentTasteExperiment
    render_concurrency: int = 2
    _locks: dict[str, asyncio.Lock] = field(default_factory=dict, init=False, repr=False)
    _renderer: BoundedGalleryRenderer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._renderer = BoundedGalleryRenderer(
            self.service,
            self.render_concurrency,
        )

    async def generate(
        self,
        session_id: str,
        taste_id: str,
        request: TasteGalleryRequest,
    ) -> dict[str, Any]:
        async with self._lock_for(session_id):
            existing = self._find_request_event(
                session_id,
                GALLERY_EVENT_KIND,
                request.request_id,
            )
            if existing is not None:
                return public_gallery(
                    TasteGalleryManifest.model_validate(existing["payload"])
                )

            snapshot = await self.emergent.get_snapshot(session_id)
            self._validate_expected_mutation(snapshot, request)
            component = next(
                (
                    item
                    for item in snapshot["emergent_tastes"]["components"]
                    if item["taste_id"] == taste_id
                ),
                None,
            )
            if component is None:
                raise NotFoundError("taste is not present in the current projection")

            center = np.asarray(component["center"], dtype=np.float64)
            center_digest = hashlib.sha256(center.astype("<f8").tobytes()).hexdigest()
            scope = representation_scope(
                snapshot,
                self.service.renderer.capabilities(),
            )
            identity = gallery_id(
                session_id=session_id,
                taste_id=taste_id,
                center_digest=center_digest,
                scope_id=str(scope["scope_id"]),
                row_count=request.row_count,
                strengths=request.strengths,
                seed_nonce=request.seed_nonce,
            )
            prior = self._find_gallery_event(session_id, identity)
            if prior is not None:
                return public_gallery(
                    TasteGalleryManifest.model_validate(prior["payload"])
                )

            seeds = gallery_seeds(
                identity,
                int(snapshot["world"]["seed"]),
                request.row_count,
            )
            specs = cell_specs(
                identity=identity,
                center=center,
                seeds=seeds,
                strengths=request.strengths,
                artifacts_dir=self.service.settings.artifacts_dir,
            )
            artifacts = await self._renderer.render(snapshot["prompt"], specs)
            cells = [
                TasteGalleryCell(
                    cell_id=str(spec["cell_id"]),
                    row=int(spec["row"]),
                    column=int(spec["column"]),
                    seed=int(spec["seed"]),
                    strength=float(spec["strength"]),
                    action=np.asarray(spec["action"], dtype=np.float64)
                    .astype(float)
                    .tolist(),
                    clipped=bool(spec["clipped"]),
                    design_id=str(spec["design_id"]),
                    image_url=f"/assets/{spec['design_id']}.png",
                    image_digest=artifact.digest,
                    image_path=str(artifact.path),
                    feature_vector=artifact.feature_vector,
                )
                for spec, artifact in zip(specs, artifacts, strict=True)
            ]
            manifest = TasteGalleryManifest(
                gallery_id=identity,
                request_id=request.request_id,
                source_session_id=session_id,
                taste_id=taste_id,
                taste_label=str(component["label"]),
                center=center.astype(float).tolist(),
                center_digest=center_digest,
                representation_scope_id=str(scope["scope_id"]),
                representation_scope=scope,
                prompt=snapshot["prompt"],
                renderer_revision=self.service.renderer.revision,
                row_count=request.row_count,
                strengths=request.strengths,
                seeds=seeds,
                seed_nonce=request.seed_nonce,
                cells=cells,
            )
            self.service.store.append_event(
                session_id,
                GALLERY_EVENT_KIND,
                manifest.model_dump(mode="json"),
            )
            return public_gallery(manifest)

    async def get(self, session_id: str, gallery_id_value: str) -> dict[str, Any]:
        await self.service.get_snapshot(session_id)
        event = self._find_gallery_event(session_id, gallery_id_value)
        if event is None:
            raise NotFoundError("taste gallery was not found")
        return public_gallery(TasteGalleryManifest.model_validate(event["payload"]))

    async def activate(
        self,
        session_id: str,
        gallery_id_value: str,
        cell_id: str,
        payload: TasteGalleryActivationPayload,
    ) -> dict[str, Any]:
        async with self._lock_for(session_id):
            existing = self._find_request_event(
                session_id,
                GALLERY_ACTIVATED_EVENT_KIND,
                payload.request_id,
            )
            if existing is not None:
                return await self.emergent.get_snapshot(
                    str(existing["payload"]["new_session_id"])
                )

            source = await self.service.get_snapshot(session_id)
            self._validate_expected_mutation(source, payload)
            gallery_event = self._find_gallery_event(session_id, gallery_id_value)
            if gallery_event is None:
                raise NotFoundError("taste gallery was not found")
            manifest = TasteGalleryManifest.model_validate(gallery_event["payload"])
            cell = next((item for item in manifest.cells if item.cell_id == cell_id), None)
            if cell is None:
                raise NotFoundError("taste gallery cell was not found")
            if manifest.renderer_revision != self.service.renderer.revision:
                raise ConflictError("gallery renderer revision no longer matches the runtime")

            new_session_id = gallery_session_id(session_id, payload.request_id)
            try:
                await self.service.get_snapshot(new_session_id)
            except NotFoundError:
                await create_session_from_cell(
                    self.service,
                    new_session_id=new_session_id,
                    source_snapshot=source,
                    manifest=manifest,
                    cell=cell,
                )

            event_payload = {
                "request_id": payload.request_id,
                "gallery_id": gallery_id_value,
                "cell_id": cell_id,
                "taste_id": manifest.taste_id,
                "source_session_id": session_id,
                "new_session_id": new_session_id,
                "seed": cell.seed,
                "strength": cell.strength,
                "action": cell.action,
                "preference_effect": "none",
                "created_at": utc_now(),
            }
            self.service.store.append_event(
                session_id,
                GALLERY_ACTIVATED_EVENT_KIND,
                event_payload,
            )
            self.service.store.append_event(
                new_session_id,
                GALLERY_SESSION_EVENT_KIND,
                event_payload,
            )
            augmented = await self.emergent.get_snapshot(new_session_id)
            augmented["gallery_origin"] = event_payload
            return augmented

    def _find_request_event(
        self,
        session_id: str,
        kind: str,
        request_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                event
                for event in reversed(self.service.store.list_events(session_id))
                if event["kind"] == kind
                and event["payload"].get("request_id") == request_id
            ),
            None,
        )

    def _find_gallery_event(
        self,
        session_id: str,
        gallery_id_value: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                event
                for event in reversed(self.service.store.list_events(session_id))
                if event["kind"] == GALLERY_EVENT_KIND
                and event["payload"].get("gallery_id") == gallery_id_value
            ),
            None,
        )

    @staticmethod
    def _validate_expected_mutation(
        snapshot: dict[str, Any],
        payload: CommandPayload,
    ) -> None:
        expected = payload.resolved_expected_mutation_version()
        if expected is not None and expected != snapshot["mutation_version"]:
            raise ConflictError(
                f"session mutation version is stale: expected {expected}, "
                f"current {snapshot['mutation_version']}"
            )

    def _lock_for(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock
