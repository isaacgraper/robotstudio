"""FastAPI application for Robotstudio."""

from __future__ import annotations

import os
from pathlib import Path

import robot
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from robotstudio import __version__
from robotstudio.api.schemas import (
    DocumentRequest,
    HealthResponse,
    InitResponse,
    PreviewResponse,
    RunRequest,
    RunResponse,
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
from robotstudio.runner import (
    RunBusyError,
    RunError,
    RunSummary,
    export_run,
    list_runs,
    load_run,
    run_suite,
)
from robotstudio.settings import allow_run_from_env
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import SuiteEntry, Workspace, WorkspaceError

WEB_DIST = Path(__file__).resolve().parent.parent / "web_dist"


def default_workspace() -> Path:
    """Return the configured workspace directory."""
    return Path(os.environ.get("ROBOTSTUDIO_WORKSPACE", "workspace"))


def create_app(
    workspace: Path | str | None = None,
    *,
    allow_run: bool | None = None,
) -> FastAPI:
    """Build the Robotstudio application.

    ``allow_run`` defaults to the ``ROBOTSTUDIO_ALLOW_RUN`` environment switch.
    """
    app = FastAPI(
        title="Robotstudio",
        version=__version__,
        description="Visual authoring and execution for Robot Framework.",
    )
    app.state.workspace = Workspace(workspace or default_workspace())
    app.state.allow_run = allow_run_from_env() if allow_run is None else allow_run
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
            allow_run=app.state.allow_run,
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

    @app.post("/api/suites/{stem}/run", response_model=RunResponse)
    def run(stem: str, request: RunRequest | None = None) -> RunResponse:
        if not app.state.allow_run:
            raise HTTPException(status_code=403, detail="Suite execution is disabled")
        options = request or RunRequest()
        try:
            summary = run_suite(
                _store(app),
                stem,
                timeout=options.timeout,
                redact_patterns=tuple(options.redact),
            )
        except RunBusyError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RunError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return _run_response(summary)

    @app.get("/api/runs", response_model=list[RunResponse])
    def runs() -> list[RunResponse]:
        return [_run_response(summary) for summary in list_runs(_store(app))]

    @app.get("/api/runs/{run_id}", response_model=RunResponse)
    def run_detail(run_id: str) -> RunResponse:
        try:
            return _run_response(load_run(_store(app), run_id))
        except RunError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/runs/{run_id}/export/{export}")
    def run_export(run_id: str, export: str) -> FileResponse:
        try:
            path, media_type = export_run(_store(app), run_id, export)
        except RunError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(path, media_type=media_type, filename=path.name)

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


def _run_response(summary: RunSummary) -> RunResponse:
    return RunResponse(
        run_id=summary.run_id,
        stem=summary.stem,
        status=summary.status,
        started_at=summary.started_at,
        finished_at=summary.finished_at,
        duration_ms=summary.duration_ms,
        total=summary.total,
        passed=summary.passed,
        failed=summary.failed,
        skipped=summary.skipped,
        cases=[case.model_dump() for case in summary.cases],
        output_dir=summary.output_dir,
        error=summary.error,
    )


LLMS_TXT = """# Robotstudio

Robotstudio is a visual authoring, execution and export platform for Robot
Framework. It stores each suite as a canvas document (`*.canvas.json`) and
generates deterministic `.robot` source.

## CLI

    robotstudio init    [--workspace DIR] [--force]
    robotstudio serve   [--workspace DIR] [--host HOST] [--port PORT]
    robotstudio generate DOCUMENT.json [--out FILE.robot]
    robotstudio validate DOCUMENT.json [--dry-run]
    robotstudio catalog [--library NAME] [--curated]
    robotstudio run     STEM [--workspace DIR] [--timeout SECONDS]
    robotstudio runs    [--workspace DIR]
    robotstudio export  RUN_ID FORMAT [--workspace DIR] [--out FILE]
    robotstudio mcp     [--workspace DIR]

Export formats: junit, results-csv, cases-csv, results-json, bundle.

## HTTP API

- GET  /api/health
- GET  /api/catalog
- GET  /api/suites
- POST /api/suites
- GET  /api/suites/{stem}
- PUT  /api/suites/{stem}
- DEL  /api/suites/{stem}
- POST /api/suites/{stem}/run
- GET  /api/runs
- GET  /api/runs/{run_id}
- GET  /api/runs/{run_id}/export/{format}
- POST /api/preview
- POST /api/validate
- POST /api/init
- GET  /openapi.json

## MCP

Run `robotstudio mcp` for a stdio MCP server (needs the `mcp` extra).
Tools are prefixed `studio_`: list_suites, get_suite, save_suite,
delete_suite, read_robot, import_robot, preview, validate, search_keywords,
describe_keyword, list_libraries, refresh_catalog, run_suite, list_runs,
get_run, export_run.

## Workspace

    <workspace>/<stem>.canvas.json   authored document
    <workspace>/<stem>.robot         generated source
    <workspace>/.runs/<run_id>/      results, console log, robot artifacts

One run at a time. Runs have a hard timeout and write only inside the
workspace.
"""


def _register_web(app: FastAPI) -> None:
    @app.get("/llms.txt", include_in_schema=False, response_class=PlainTextResponse)
    def llms_txt() -> str:
        return LLMS_TXT

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
