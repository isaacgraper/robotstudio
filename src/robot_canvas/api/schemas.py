"""Request and response schemas for the Robot Canvas API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from robot_canvas.model.canvas import CanvasDocument


class DocumentRequest(BaseModel):
    """A canvas document submitted by the editor."""

    document: CanvasDocument
    stem: str | None = None


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


class ValidationRequest(BaseModel):
    """A document to validate, optionally with a hardware-free dry run."""

    document: CanvasDocument
    dry_run: bool = False


class InitResponse(BaseModel):
    """Result of creating the starter suite."""

    created: bool
    suite: SavedSuiteResponse
