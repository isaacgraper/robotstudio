"""FastAPI application for Robotstudio."""

from __future__ import annotations

import os
from pathlib import Path

import robot
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from robotstudio import __version__
from robotstudio.api.schemas import (
    DocumentRequest,
    HealthResponse,
    InitResponse,
    PreviewResponse,
    SavedSuiteResponse,
    SuiteResponse,
    ValidationRequest,
)
from robotstudio.generator.validation import dry_run, parse_source
from robotstudio.keywords.catalog import (
    Catalog,
    clear_catalog_cache,
    configured_libraries,
    load_catalog,
)
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import SuiteEntry, Workspace, WorkspaceError

WEB_DIST = Path(__file__).resolve().parent.parent / "web_dist"


def default_workspace() -> Path:
    """Return the configured workspace directory."""
    return Path(os.environ.get("ROBOTSTUDIO_WORKSPACE", "workspace"))


def create_app(workspace: Path | str | None = None) -> FastAPI:
    """Build the Robotstudio application."""
    app = FastAPI(
        title="Robotstudio",
        version=__version__,
        description="Visual authoring and execution for Robot Framework.",
    )
    app.state.workspace = Workspace(workspace or default_workspace())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_api(app)
    _register_web(app)
    logger.info("Robotstudio workspace: {}", app.state.workspace.root)
    return app


def _store(app: FastAPI) -> Workspace:
    workspace: Workspace = app.state.workspace
    return workspace


def _register_api(app: FastAPI) -> None:
    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        workspace = _store(app)
        return HealthResponse(
            version=__version__,
            robot_version=robot.version.VERSION,  # type: ignore[attr-defined]
            workspace=str(workspace.root),
            libraries=configured_libraries(),
        )

    @app.get("/api/catalog", response_model=Catalog)
    def catalog() -> Catalog:
        return load_catalog()

    @app.post("/api/catalog/refresh", response_model=Catalog)
    def refresh_catalog() -> Catalog:
        clear_catalog_cache()
        return load_catalog()

    @app.get("/api/suites", response_model=list[SuiteEntry])
    def list_suites() -> list[SuiteEntry]:
        return _store(app).list_suites()

    @app.post("/api/suites", response_model=SavedSuiteResponse)
    def save_suite(request: DocumentRequest) -> SavedSuiteResponse:
        workspace = _store(app)
        try:
            saved = workspace.save(request.document, request.stem)
        except WorkspaceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        validation = parse_source(saved.robot_text)
        return SavedSuiteResponse(
            stem=saved.stem,
            canvas_path=str(saved.canvas_path),
            robot_path=str(saved.robot_path),
            robot_text=saved.robot_text,
            validation=validation.as_dict(),
        )

    @app.get("/api/suites/{stem}", response_model=SuiteResponse)
    def get_suite(stem: str) -> SuiteResponse:
        workspace = _store(app)
        try:
            document = workspace.load(stem)
            robot_text = workspace.robot_text(stem)
        except WorkspaceError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return SuiteResponse(stem=stem, document=document, robot_text=robot_text)

    @app.put("/api/suites/{stem}", response_model=SavedSuiteResponse)
    def update_suite(stem: str, request: DocumentRequest) -> SavedSuiteResponse:
        workspace = _store(app)
        try:
            saved = workspace.save(request.document, stem)
        except WorkspaceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        validation = parse_source(saved.robot_text)
        return SavedSuiteResponse(
            stem=stem,
            canvas_path=str(saved.canvas_path),
            robot_path=str(saved.robot_path),
            robot_text=saved.robot_text,
            validation=validation.as_dict(),
        )

    @app.delete("/api/suites/{stem}")
    def delete_suite(stem: str) -> dict[str, bool]:
        workspace = _store(app)
        try:
            workspace.delete(stem)
        except WorkspaceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"deleted": True}

    @app.post("/api/preview", response_model=PreviewResponse)
    def preview(request: DocumentRequest) -> PreviewResponse:
        try:
            robot_text = request.document.robot_text()
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return PreviewResponse(
            robot_text=robot_text,
            validation=parse_source(robot_text).as_dict(),
        )

    @app.post("/api/validate", response_model=PreviewResponse)
    def validate(request: ValidationRequest) -> PreviewResponse:
        robot_text = request.document.robot_text()
        result = (
            dry_run(robot_text, _store(app).root)
            if request.dry_run
            else parse_source(robot_text)
        )
        return PreviewResponse(robot_text=robot_text, validation=result.as_dict())

    @app.post("/api/init", response_model=InitResponse)
    def init_workspace() -> InitResponse:
        workspace = _store(app)
        document = demo_document()
        created = not workspace.canvas_path("robotstudio-demo").is_file()
        saved = workspace.save(document, "robotstudio-demo")
        validation = parse_source(saved.robot_text)
        return InitResponse(
            created=created,
            suite=SavedSuiteResponse(
                stem=saved.stem,
                canvas_path=str(saved.canvas_path),
                robot_path=str(saved.robot_path),
                robot_text=saved.robot_text,
                validation=validation.as_dict(),
            ),
        )


def _register_web(app: FastAPI) -> None:
    index = WEB_DIST / "index.html"
    if not index.is_file():

        @app.get("/")
        def api_only() -> dict[str, str]:
            return {
                "name": "Robotstudio",
                "version": __version__,
                "message": "Frontend assets are not built. Run the Vite dev server.",
            }

        return
    assets = WEB_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def index_page() -> FileResponse:
        return FileResponse(index)

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        candidate = WEB_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)
