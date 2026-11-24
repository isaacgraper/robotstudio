"""Workspace management for Robotstudio."""

from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import (
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
