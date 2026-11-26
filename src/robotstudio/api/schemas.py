"""Request and response schemas for the Robotstudio API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from robotstudio.model.canvas import CanvasDocument


class DocumentRequest(BaseModel):
    """A canvas document submitted by the editor."""

    document: CanvasDocument
    stem: str | None = None


class NewSuiteRequest(BaseModel):
    """A name for a new, empty suite."""

    name: str


class PreviewResponse(BaseModel):
    """Generated source and validation outcome for a document."""

    robot_text: str
    validation: dict[str, object]


class SavedSuiteResponse(BaseModel):
    """A suite that was written to the workspace."""

    stem: str
    canvas_path: str
    robot_path: str
    robot_text: str
    validation: dict[str, object]


class SuiteResponse(BaseModel):
    """A stored suite with its document and generated source."""

    stem: str
    document: CanvasDocument
    robot_text: str


class HealthResponse(BaseModel):
    """Basic runtime information."""

    status: str = "ok"
    version: str
    robot_version: str
    workspace: str
    libraries: list[str] = Field(default_factory=list)
    allow_run: bool = True


class ValidationRequest(BaseModel):
    """A document to validate, optionally with a hardware-free dry run."""

    document: CanvasDocument
    dry_run: bool = False


class InitResponse(BaseModel):
    """Result of creating the starter suite."""

    created: bool
    suite: SavedSuiteResponse


class RunRequest(BaseModel):
    """Options for executing a stored suite."""

    timeout: float = 600.0
    redact: list[str] = Field(default_factory=list)


class RunResponse(BaseModel):
    """Outcome of a suite run."""

    run_id: str
    stem: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: int
    total: int
    passed: int
    failed: int
    skipped: int
    cases: list[dict[str, object]] = Field(default_factory=list)
    output_dir: str
    error: str | None = None
