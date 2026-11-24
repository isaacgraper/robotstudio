"""Workspace storage for canvas documents and generated suites."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from robotstudio.generator.writer import write_document
from robotstudio.model.canvas import CanvasDocument

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")
_STEM = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SUFFIX = ".canvas.json"


class WorkspaceError(Exception):
    """Raised for invalid workspace operations."""


@dataclass(slots=True)
class SuiteEntry:
    """Summary of one stored suite."""

    stem: str
    name: str
    tests: int
    keywords: int
    updated: str
    canvas_path: str
    robot_path: str


@dataclass(slots=True)
class SavedSuite:
    """Result of saving a document."""

    stem: str
    canvas_path: Path
    robot_path: Path
    robot_text: str


def slugify(name: str) -> str:
    """Turn a document name into a safe file stem."""
    slug = _SLUG_INVALID.sub("-", name.strip().lower()).strip("-")
    return slug or "suite"


class Workspace:
    """A directory containing canvas documents and generated suites."""

    def __init__(self, root: Path | str) -> None:
        """Initialize a workspace at ``root``."""
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _check_stem(self, stem: str) -> str:
        if not stem or not _STEM.match(stem):
            raise WorkspaceError(f"Invalid suite name: {stem!r}")
        return stem

    def canvas_path(self, stem: str) -> Path:
        """Return the sidecar path for ``stem``."""
        return self.root / (self._check_stem(stem) + _SUFFIX)

    def robot_path(self, stem: str) -> Path:
        """Return the generated Robot path for ``stem``."""
        return self.root / (self._check_stem(stem) + ".robot")

    def list_suites(self) -> list[SuiteEntry]:
        """List every stored suite, newest first."""
        entries: list[SuiteEntry] = []
        for path in self.root.glob("*" + _SUFFIX):
            try:
                document = CanvasDocument.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue
            updated = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
            stem = path.name[: -len(_SUFFIX)]
            entries.append(
                SuiteEntry(
                    stem=stem,
                    name=document.name,
                    tests=len(document.tests),
                    keywords=len(document.keywords),
                    updated=updated,
                    canvas_path=str(path),
                    robot_path=str(self.robot_path(stem)),
                )
            )
        entries.sort(key=lambda entry: entry.updated, reverse=True)
        return entries

    def load(self, stem: str) -> CanvasDocument:
        """Load a document by file stem."""
        path = self.canvas_path(stem)
        if not path.is_file():
            raise WorkspaceError(f"Suite not found: {stem}")
        try:
            return CanvasDocument.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise WorkspaceError(f"Suite is not valid JSON: {error}") from error

    def save(self, document: CanvasDocument, stem: str | None = None) -> SavedSuite:
        """Write the sidecar document and the generated Robot suite."""
        if stem is None:
            stem = slugify(document.name)
        stem = self._check_stem(stem)
        robot_text = write_document(document)
        canvas_path = self.canvas_path(stem)
        robot_path = self.robot_path(stem)
        _atomic_write(
            canvas_path,
            json.dumps(document.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
        )
        _atomic_write(robot_path, robot_text)
        return SavedSuite(
            stem=stem,
            canvas_path=canvas_path,
            robot_path=robot_path,
            robot_text=robot_text,
        )

    def delete(self, stem: str) -> None:
        """Delete both files for a suite."""
        self.canvas_path(stem).unlink(missing_ok=True)
        self.robot_path(stem).unlink(missing_ok=True)

    def robot_text(self, stem: str) -> str:
        """Read the generated Robot source for a suite."""
        path = self.robot_path(stem)
        if not path.is_file():
            raise WorkspaceError(f"Generated suite not found: {stem}")
        return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, text: str) -> None:
    """Write text through a temporary file and an atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".robotstudio-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
