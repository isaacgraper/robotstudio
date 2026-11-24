"""Workspace management for Robot Canvas."""

from robot_canvas.workspace.demo import demo_document
from robot_canvas.workspace.store import (
    SavedSuite,
    SuiteEntry,
    Workspace,
    WorkspaceError,
    slugify,
)

__all__ = [
    "SavedSuite",
    "SuiteEntry",
    "Workspace",
    "WorkspaceError",
    "demo_document",
    "slugify",
]
