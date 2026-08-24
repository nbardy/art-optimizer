from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import numpy as np
from pydantic import Field, field_validator, model_validator

from .domain import (
    MAX_SEED,
    BranchNode,
    CommandPayload,
    SearchState,
    SessionState,
    WorldState,
    new_id,
    utc_now,
)
from .emergent_experiment import EmergentTasteExperiment
from .emergent_taste import ContractModel
from .preference import BayesianChoiceModel
from .rendering import RenderedArtifact
from .service import ArtOptimizerService, ConflictError, NotFoundError, SessionRuntime


GALLERY_EVENT_KIND = "emergent_taste_gallery_generated"
GALLERY_ACTIVATED_EVENT_KIND = "emergent_taste_gallery_cell_activated"
GALLERY_SESSION_EVENT_KIND = "emergent_taste_gallery_session_started"
DEFAULT_STRENGTHS = [0.25, 0.5, 0.75, 1.0, 1.25]


class TasteGalleryRequest(CommandPayload):
    row_count: int = Field(default=4, ge=1, le=6)
    strengths: list[float] = Field(
        default_factory=lambda: list(DEFAULT_STRENGTHS),
        min_length=2,
        max_length=7,
    )
    seed_nonce: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("strengths")
    @classmethod
    def validate_strengths(cls, value: list[float]) -> list[float]:
        normalized = [float(item) for item in value]
        if any(not np.isfinite(item) or not 0.0 <= item <= 3.0 for item in normalized):
            raise ValueError("gallery strengths must be finite values in [0, 3]")
        if len(normalized) != len(set(normalized)):
            raise ValueError("gallery strengths must be unique")
        return normalized


class TasteGalleryActivationPayload(CommandPayload):
    pass


class TasteGalleryCell(ContractModel):
    cell_id: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    seed: int = Field(ge=0, le=MAX_SEED)
    strength: float = Field(ge=0.0, le=3.0)
    action: list[float]
    clipped: bool
    design_id: str
    image_url: str
    image_digest: str
    image_path: str
    feature_vector: list[float]


class TasteGalleryManifest(ContractModel):
    gallery_id: str
    request_id: str
    source_session_id: str
    taste_id: str
    taste_label: str
    center: list[float]
    center_digest: str
    representation_scope_id: str
    representation_scope: dict[str, object]
    prompt: str
    renderer_revision: str
    row_count: int
    strengths: list[float]
    seeds: list[int]
    seed_nonce: int
    cells: list[TasteGalleryCell]
    preference_effect: str = "none"
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_grid(self) -> Self:
        expected = self.row_count * len(self.strengths)
        if len(self.cells) != expected:
            raise ValueError("gallery cell count does not match rows × strengths")
        if len(self.seeds) != self.row_count:
            raise ValueError("gallery seed count does not match row_count")
        ids = [item.cell_id for item in self.cells]
        if len(ids) != len(set(ids)):
            raise ValueError("gallery cell IDs must be unique")
        return self


@dataclass(slots=True)
class TasteGalleryService:
    """Read-only seed-by-strength inspection for an emergent taste projection."""

    service: ArtOptimizerService
    emergent: EmergentTasteExperiment

    async def generate(
        self,
        session_id: str,
        taste_id: str,
        request: TasteGalleryRequest,
    ) -> dict[str, Any]:
        existing = self._find_request_event(
            session_id,
            GALLERY_EVENT_KIND,
            request.request_id,
        )
        if existing is not None:
            return self._public_gallery(
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
        scope = self._representation_scope(snapshot)
        gallery_id = self._gallery_id(
            session_id=session_id,
            taste_id=taste_id,
            center_digest=center_digest,
            scope_id=str(scope["scope_id"]),
            row_count=request.row_count,
            strengths=request.strengths,
            seed_nonce=request.seed_nonce,
        )
        prior = self._find_gallery_event(session_id, gallery_id)
        if prior is not None:
            return self._public_gallery(
                TasteGalleryManifest.model_validate(prior["payload"])
            )

        seeds = self._gallery_seeds(
            gallery_id,
            int(snapshot["world"]["seed"]),
            request.row_count,
        )
        specs: list[dict[str, object]] = []
        for row, seed in enumerate(seeds):
            for column, strength in enumerate(request.strengths):
                raw = center * float(strength)
                action = np.clip(raw, -1.0, 1.0)
                cell_id = f"cell-{row + 1}-{column + 1}"
                digest = hashlib.sha256(
                    f"{gallery_id}:{cell_id}".encode("utf-8")
                ).hexdigest()
                specs.append(
                    {
                        "cell_id": cell_id,
                        "row": row,
                        "column": column,
                        "seed": seed,
                        "strength": float(strength),
                        "action": action,
                        "clipped": bool(np.any(np.abs(raw) > 1.0)),
                        "design_id": f"gallery_{digest[:32]}",
                    }
                )

        artifacts = await asyncio.gather(
            *[
                asyncio.to_thread(
                    self.service.renderer.render,
                    design_id=str(spec["design_id"]),
                    seed=int(spec["seed"]),
                    prompt=snapshot["prompt"],
                    action=np.asarray(spec["action"], dtype=np.float64),
                )
                for spec in specs
            ]
        )
        cells = [
            TasteGalleryCell(
                cell_id=str(spec["cell_id"]),
                row=int(spec["row"]),
                column=int(spec["column"]),
                seed=int(spec["seed"]),
                strength=float(spec["strength"]),
                action=np.asarray(spec["action"], dtype=np.float64).astype(float).tolist(),
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
            gallery_id=gallery_id,
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
        return self._public_gallery(manifest)

    async def get(self, session_id: str, gallery_id: str) -> dict[str, Any]:
        await self.service.get_snapshot(session_id)
        event = self._find_gallery_event(session_id, gallery_id)
        if event is None:
            raise NotFoundError("taste gallery was not found")
        return self._public_gallery(
            TasteGalleryManifest.model_validate(event["payload"])
        )

    async def activate(
        self,
        session_id: str,
        gallery_id: str,
        cell_id: str,
        payload: TasteGalleryActivationPayload,
    ) -> dict[str, Any]:
        existing = self._find_request_event(
            session_id,
            GALLERY_ACTIVATED_EVENT_KIND,
            payload.request_id,
        )
        if existing is not None:
            new_session_id = str(existing["payload"]["new_session_id"])
            return await self.emergent.get_snapshot(new_session_id)

        source = await self.service.get_snapshot(session_id)
        self._validate_expected_mutation(source, payload)
        gallery_event = self._find_gallery_event(session_id, gallery_id)
        if gallery_event is None:
            raise NotFoundError("taste gallery was not found")
        manifest = TasteGalleryManifest.model_validate(gallery_event["payload"])
        cell = next((item for item in manifest.cells if item.cell_id == cell_id), None)
        if cell is None:
            raise NotFoundError("taste gallery cell was not found")
        if manifest.renderer_revision != self.service.renderer.revision:
            raise ConflictError("gallery renderer revision no longer matches the runtime")

        new_session_id = self._gallery_session_id(session_id, payload.request_id)
        try:
            result = await self.service.get_snapshot(new_session_id)
        except NotFoundError:
            result = await self._create_session_from_cell(
                new_session_id=new_session_id,
                source_snapshot=source,
                manifest=manifest,
                cell=cell,
            )

        event_payload = {
            "request_id": payload.request_id,
            "gallery_id": gallery_id,
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

    async def _create_session_from_cell(
        self,
        *,
        new_session_id: str,
        source_snapshot: dict[str, Any],
        manifest: TasteGalleryManifest,
        cell: TasteGalleryCell,
    ) -> dict[str, Any]:
        path = Path(cell.image_path)
        if path.exists():
            artifact = RenderedArtifact(
                path=path,
                feature_vector=cell.feature_vector,
                digest=cell.image_digest,
            )
        else:
            artifact = await asyncio.to_thread(
                self.service.renderer.render,
                design_id=cell.design_id,
                seed=cell.seed,
                prompt=manifest.prompt,
                action=np.asarray(cell.action, dtype=np.float64),
            )

        world_id = new_id("world")
        root_design = self.service._design_from_artifact(
            design_id=cell.design_id,
            world_id=world_id,
            seed=cell.seed,
            prompt=manifest.prompt,
            action=np.asarray(cell.action, dtype=np.float64),
            artifact=artifact,
        )
        model = BayesianChoiceModel(self.service.settings.action_dimension)
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
            renderer_revision=self.service.renderer.revision,
            control_basis_revision=self.service.renderer.control_basis_revision,
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
        self.service._sessions[new_session_id] = runtime
        self.service.store.record_session_event(
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
                "renderer_revision": self.service.renderer.revision,
                "control_basis_revision": self.service.renderer.control_basis_revision,
            },
        )
        await self.service._start_round(runtime)
        return await self.service._snapshot(runtime)

    def _representation_scope(self, snapshot: dict[str, Any]) -> dict[str, object]:
        current = snapshot["current_design"]
        capabilities = self.service.renderer.capabilities()
        manifest: dict[str, object] = {
            "schema": "taste-gallery-scope/v1",
            "model_id": capabilities.model_id,
            "renderer_revision": capabilities.renderer_revision,
            "codec_revision": capabilities.codec_revision,
            "conditioning_mode": capabilities.conditioning_mode,
            "control_basis_revision": current["control_basis_revision"],
            "prompt": snapshot["prompt"],
            "action_dimension": len(current["action"]),
        }
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        manifest["scope_id"] = (
            f"taste-gallery-scope/v1:{hashlib.sha256(encoded.encode()).hexdigest()}"
        )
        return manifest

    @staticmethod
    def _gallery_session_id(source_session_id: str, request_id: str) -> str:
        digest = hashlib.sha256(
            f"{source_session_id}:{request_id}".encode("utf-8")
        ).hexdigest()
        return f"session_{digest[:32]}"

    @staticmethod
    def _gallery_id(
        *,
        session_id: str,
        taste_id: str,
        center_digest: str,
        scope_id: str,
        row_count: int,
        strengths: list[float],
        seed_nonce: int,
    ) -> str:
        encoded = json.dumps(
            {
                "session_id": session_id,
                "taste_id": taste_id,
                "center_digest": center_digest,
                "scope_id": scope_id,
                "row_count": row_count,
                "strengths": strengths,
                "seed_nonce": seed_nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"taste_gallery_{digest[:24]}"

    @staticmethod
    def _gallery_seeds(gallery_id: str, current_seed: int, row_count: int) -> list[int]:
        seeds = [current_seed]
        for row in range(1, row_count):
            nonce = 0
            while True:
                material = f"{gallery_id}:row:{row}:nonce:{nonce}".encode("utf-8")
                seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "little")
                seed &= MAX_SEED
                if seed not in seeds:
                    seeds.append(seed)
                    break
                nonce += 1
        return seeds

    @staticmethod
    def _public_gallery(manifest: TasteGalleryManifest) -> dict[str, Any]:
        payload = manifest.model_dump(mode="json")
        for cell in payload["cells"]:
            cell.pop("image_path", None)
            cell.pop("feature_vector", None)
        payload["axis"] = {
            "vertical": "seed",
            "horizontal": "taste strength",
            "strength_formula": "clip(strength × taste_center, -1, 1)",
        }
        return payload

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
        gallery_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                event
                for event in reversed(self.service.store.list_events(session_id))
                if event["kind"] == GALLERY_EVENT_KIND
                and event["payload"].get("gallery_id") == gallery_id
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
                "session mutation version is stale: "
                f"expected {expected}, current {snapshot['mutation_version']}"
            )
