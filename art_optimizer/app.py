from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .composition import build_service
from .config import Settings
from .domain import (
    CommitPayload,
    CreateSessionRequest,
    ExposurePayload,
    FavoritePayload,
    NewWorldPayload,
    RestorePayload,
)
from .model_codec import model_catalog
from .service import ConflictError, NotFoundError, OperationError
from .ui_experiments import (
    get_ui_experiment,
    selected_ui_id,
    ui_catalog,
    validate_ui_files,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    service = build_service(settings)
    default_static_dir = Path(__file__).with_name("static").resolve()
    static_dir = Path(
        os.environ.get("ART_OPTIMIZER_STATIC_DIR", str(default_static_dir))
    ).expanduser().resolve()
    bundled_ui = static_dir == default_static_dir
    if bundled_ui:
        validate_ui_files(static_dir)
        default_ui = get_ui_experiment(selected_ui_id())
        root_filename = default_ui.filename
        active_ui_id = default_ui.experiment_id
    else:
        root_filename = "index.html"
        if not (static_dir / root_filename).is_file():
            raise ValueError(f"custom UI directory has no index.html: {static_dir}")
        active_ui_id = "custom"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await service.shutdown()

    app = FastAPI(title="Art Optimizer", version="0.4.0", lifespan=lifespan)
    app.state.service = service
    app.mount("/assets", StaticFiles(directory=settings.artifacts_dir), name="assets")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(error).strip("'")}, status_code=404)

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, error: ConflictError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(OperationError)
    async def handle_operation_error(_: Request, error: OperationError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=500)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / root_filename)

    @app.get("/ui/{experiment_id}")
    async def experiment_ui(experiment_id: str) -> FileResponse:
        if not bundled_ui:
            raise HTTPException(
                status_code=404,
                detail="bundled UI experiments are unavailable under ART_OPTIMIZER_STATIC_DIR",
            )
        try:
            experiment = get_ui_experiment(experiment_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error).strip("'")) from error
        return FileResponse(static_dir / experiment.filename)

    @app.get("/healthz")
    async def health() -> dict[str, object]:
        database = service.store.integrity_check()
        capabilities = service.renderer.capabilities()
        return {
            "ok": database == "ok",
            "database": database,
            "model": capabilities.model_id,
            "renderer": capabilities.renderer_revision,
            "codec": capabilities.codec_revision,
            "control_basis": capabilities.control_basis_revision,
            "conditioning_mode": capabilities.conditioning_mode,
            "replay_level": capabilities.replay_level,
            "open_weights": capabilities.open_weights,
            "osi_open_source": capabilities.osi_open_source,
            "content_filter_required": capabilities.content_filter_required,
            "license_id": capabilities.license_id,
            "license_url": capabilities.license_url,
            "ui": active_ui_id,
            "data_dir": str(settings.data_dir),
        }

    @app.get("/api/models")
    async def models() -> list[dict[str, object]]:
        return model_catalog()

    @app.get("/api/ui-experiments")
    async def ui_experiments() -> list[dict[str, str]]:
        return ui_catalog()

    @app.post("/api/sessions")
    async def create_session(request: CreateSessionRequest) -> dict[str, object]:
        return await service.create_session(request)

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, object]:
        return await service.get_snapshot(session_id)

    @app.get("/api/sessions/{session_id}/events")
    async def stream_events(session_id: str) -> StreamingResponse:
        return StreamingResponse(
            service.stream(session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/sessions/{session_id}/event-log")
    async def event_log(session_id: str) -> list[dict[str, object]]:
        return await service.events(session_id)

    @app.post("/api/sessions/{session_id}/candidates/{candidate_id}/commit")
    async def commit_candidate(
        session_id: str,
        candidate_id: str,
        payload: CommitPayload,
    ) -> dict[str, object]:
        return await service.commit_candidate(session_id, candidate_id, payload)

    @app.post("/api/sessions/{session_id}/reroll")
    async def reroll(session_id: str, payload: ExposurePayload) -> dict[str, object]:
        return await service.reroll(session_id, payload)

    @app.post("/api/sessions/{session_id}/new-world")
    async def new_world(
        session_id: str,
        payload: NewWorldPayload,
    ) -> dict[str, object]:
        return await service.new_world(session_id, payload)

    @app.post("/api/sessions/{session_id}/designs/{design_id}/favorite")
    async def favorite(
        session_id: str,
        design_id: str,
        payload: FavoritePayload,
    ) -> dict[str, object]:
        return await service.favorite(session_id, design_id, payload)

    @app.post("/api/sessions/{session_id}/history/{branch_node_id}/restore")
    async def restore(
        session_id: str,
        branch_node_id: str,
        payload: RestorePayload,
    ) -> dict[str, object]:
        return await service.restore(session_id, branch_node_id, payload)

    return app


app = create_app()


def run() -> None:
    parser = argparse.ArgumentParser(description="Run the Art Optimizer development server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("art_optimizer.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    run()
