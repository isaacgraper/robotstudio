"""FastMCP server exposing Robotstudio to LLM clients such as Claude."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from robotstudio import __version__
from robotstudio.generator.validation import dry_run, parse_source
from robotstudio.keywords.catalog import clear_catalog_cache, load_catalog
from robotstudio.model.canvas import CanvasDocument
from robotstudio.runner import (
    RunBusyError,
    RunError,
    export_run,
    list_runs,
    load_run,
    run_suite,
)
from robotstudio.workspace.import_robot import import_robot_file
from robotstudio.workspace.store import Workspace

DEFAULT_WORKSPACE = "workspace"


def workspace_root() -> Path:
    """Resolve the workspace directory from the environment."""
    return Path(os.environ.get("ROBOTSTUDIO_WORKSPACE", DEFAULT_WORKSPACE)).expanduser()


def _workspace() -> Workspace:
    return Workspace(workspace_root())


def _suite_summary(entry: Any) -> dict[str, Any]:
    return {
        "stem": entry.stem,
        "name": entry.name,
        "tests": entry.tests,
        "keywords": entry.keywords,
        "updated": entry.updated,
    }


def create_server() -> FastMCP:
    """Build the MCP server with every Robotstudio tool registered."""
    mcp = FastMCP(
        "robotstudio",
        instructions=(
            "Robotstudio is a visual authoring and execution platform for Robot "
            "Framework. Use these tools to inspect the keyword catalog, create and "
            "edit canvas suites, generate and validate Robot source, run suites, "
            "and export results. Always search the catalog before inventing a "
            "keyword name."
        ),
    )

    # -- workspace ---------------------------------------------------------
    @mcp.tool()
    def studio_list_suites() -> dict[str, Any]:
        """List the suites stored in the workspace."""
        entries = _workspace().list_suites()
        return {
            "workspace": str(workspace_root()),
            "count": len(entries),
            "suites": [_suite_summary(entry) for entry in entries],
        }

    @mcp.tool()
    def studio_get_suite(stem: str) -> dict[str, Any]:
        """Load one suite as a canvas document plus its generated Robot source."""
        workspace = _workspace()
        document = workspace.load(stem)
        return {
            "stem": stem,
            "document": document.model_dump(mode="json"),
            "robot_text": workspace.robot_text(stem),
        }

    @mcp.tool()
    def studio_save_suite(
        document: dict[str, Any], stem: str | None = None
    ) -> dict[str, Any]:
        """Create or overwrite a suite from a canvas document.

        Pass the full canvas document. When ``stem`` is omitted it is derived
        from the document name.
        """
        workspace = _workspace()
        parsed = CanvasDocument.model_validate(document)
        saved = workspace.save(parsed, stem)
        validation = parse_source(saved.robot_text)
        return {
            "stem": saved.stem,
            "canvas_path": str(saved.canvas_path),
            "robot_path": str(saved.robot_path),
            "robot_text": saved.robot_text,
            "validation": _validation_payload(validation),
        }

    @mcp.tool()
    def studio_delete_suite(stem: str) -> dict[str, Any]:
        """Delete a suite and its generated Robot file."""
        workspace = _workspace()
        workspace.load(stem)
        workspace.delete(stem)
        return {"deleted": stem}

    @mcp.tool()
    def studio_read_robot(stem: str) -> dict[str, Any]:
        """Return the generated Robot Framework source for a suite."""
        return {"stem": stem, "robot_text": _workspace().robot_text(stem)}

    @mcp.tool()
    def studio_import_robot(path: str, stem: str | None = None) -> dict[str, Any]:
        """Import an existing ``.robot`` file into the workspace as a canvas suite."""
        workspace = _workspace()
        document = import_robot_file(Path(path))
        saved = workspace.save(document, stem)
        return {
            "stem": saved.stem,
            "name": document.name,
            "tests": len(document.tests),
            "keywords": len(document.keywords),
            "canvas_path": str(saved.canvas_path),
        }

    # -- authoring ---------------------------------------------------------
    @mcp.tool()
    def studio_preview(document: dict[str, Any]) -> dict[str, Any]:
        """Render a canvas document to Robot source and parse the result."""
        parsed = CanvasDocument.model_validate(document)
        robot_text = parsed.robot_text()
        return {
            "robot_text": robot_text,
            "validation": _validation_payload(parse_source(robot_text)),
        }

    @mcp.tool()
    def studio_validate(
        document: dict[str, Any] | None = None,
        stem: str | None = None,
        dry_run_check: bool = False,
    ) -> dict[str, Any]:
        """Validate a document, or a stored suite when ``stem`` is given.

        Set ``dry_run_check`` to execute Robot's own dry run, which catches
        unknown keywords and bad argument counts without touching hardware.
        """
        workspace = _workspace()
        if document is not None:
            parsed = CanvasDocument.model_validate(document)
            base = workspace.root
        elif stem is not None:
            parsed = workspace.load(stem)
            base = workspace.root
        else:
            raise ValueError("Provide either a document or a stem")
        robot_text = parsed.robot_text()
        result = (
            dry_run(robot_text, base) if dry_run_check else parse_source(robot_text)
        )
        return _validation_payload(result)

    # -- catalog -----------------------------------------------------------
    @mcp.tool()
    def studio_search_keywords(
        query: str = "",
        library: str | None = None,
        curated_only: bool = False,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search the Robot Framework keyword catalog.

        Matching is case-insensitive across keyword names and documentation.
        """
        catalog = load_catalog()
        needle = query.strip().lower()
        matches = []
        for keyword in catalog.keywords:
            if library and keyword.library.lower() != library.lower():
                continue
            if curated_only and not keyword.curated:
                continue
            haystack = f"{keyword.name} {keyword.short_documentation}".lower()
            if needle and needle not in haystack:
                continue
            matches.append(
                {
                    "name": keyword.name,
                    "library": keyword.library,
                    "category": keyword.category,
                    "curated": keyword.curated,
                    "deprecated": keyword.deprecated,
                    "short_documentation": keyword.short_documentation,
                    "arguments": [
                        argument.representation or argument.name
                        for argument in keyword.arguments
                    ],
                }
            )
            if len(matches) >= max(1, min(limit, 200)):
                break
        return {
            "query": query,
            "libraries": [info.name for info in catalog.libraries],
            "failures": [failure.model_dump() for failure in catalog.failures],
            "count": len(matches),
            "keywords": matches,
        }

    @mcp.tool()
    def studio_describe_keyword(
        name: str, library: str | None = None
    ) -> dict[str, Any]:
        """Return full libdoc detail for one keyword, including argument docs."""
        catalog = load_catalog()
        for keyword in catalog.keywords:
            if keyword.name.lower() != name.strip().lower():
                continue
            if library and keyword.library.lower() != library.lower():
                continue
            return keyword.model_dump(mode="json")
        raise ValueError(f"Keyword not found: {name}")

    @mcp.tool()
    def studio_list_libraries() -> dict[str, Any]:
        """List the libraries that are inspected for keywords."""
        catalog = load_catalog()
        return {
            "libraries": [info.model_dump(mode="json") for info in catalog.libraries],
            "failures": [
                failure.model_dump(mode="json") for failure in catalog.failures
            ],
        }

    @mcp.tool()
    def studio_refresh_catalog() -> dict[str, Any]:
        """Clear the libdoc cache, for example after installing a new library."""
        clear_catalog_cache()
        catalog = load_catalog()
        return {
            "libraries": len(catalog.libraries),
            "keywords": len(catalog.keywords),
        }

    # -- execution ---------------------------------------------------------
    @mcp.tool()
    def studio_run_suite(stem: str, timeout: float = 600.0) -> dict[str, Any]:
        """Execute a stored suite and return per-test results.

        Only one run can happen at a time. Output is written under
        ``<workspace>/.runs/<run_id>``.
        """
        try:
            summary = run_suite(_workspace(), stem, timeout=timeout)
        except RunBusyError as error:
            raise ValueError(f"Run already in progress: {error}") from error
        except RunError as error:
            raise ValueError(str(error)) from error
        return summary.model_dump(mode="json")

    @mcp.tool()
    def studio_list_runs(limit: int = 20) -> dict[str, Any]:
        """List recent runs, newest first."""
        summaries = list_runs(_workspace(), limit=max(1, min(limit, 200)))
        return {
            "count": len(summaries),
            "runs": [summary.model_dump(mode="json") for summary in summaries],
        }

    @mcp.tool()
    def studio_get_run(run_id: str) -> dict[str, Any]:
        """Return one recorded run by id."""
        try:
            return load_run(_workspace(), run_id).model_dump(mode="json")
        except RunError as error:
            raise ValueError(str(error)) from error

    @mcp.tool()
    def studio_export_run(
        run_id: str,
        format: str = "junit",
        redact: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export a run as junit, results-csv, cases-csv, results-json or bundle."""
        try:
            path, media_type = export_run(
                _workspace(), run_id, format, redact_patterns=tuple(redact or ())
            )
        except RunError as error:
            raise ValueError(str(error)) from error
        return {
            "path": str(path),
            "media_type": media_type,
            "bytes": path.stat().st_size,
        }

    # -- resources ---------------------------------------------------------
    @mcp.resource("robotstudio://suites")
    def suites_resource() -> str:
        """Every suite in the workspace."""
        return json.dumps(
            [_suite_summary(entry) for entry in _workspace().list_suites()], indent=2
        )

    @mcp.resource("robotstudio://suites/{stem}")
    def suite_resource(stem: str) -> str:
        """One suite as a canvas document."""
        document = _workspace().load(stem)
        return json.dumps(document.model_dump(mode="json"), indent=2)

    @mcp.resource("robotstudio://suites/{stem}/robot")
    def suite_robot_resource(stem: str) -> str:
        """The generated Robot Framework source for one suite."""
        return _workspace().robot_text(stem)

    @mcp.resource("robotstudio://runs/{run_id}")
    def run_resource(run_id: str) -> str:
        """One recorded run summary."""
        try:
            summary = load_run(_workspace(), run_id)
        except RunError as error:
            raise ValueError(str(error)) from error
        return summary.model_dump_json(indent=2)

    # -- prompts -----------------------------------------------------------
    @mcp.prompt()
    def author_suite(goal: str) -> str:
        """Draft a plan for authoring a Robot Framework suite."""
        return (
            "You are authoring a Robot Framework suite inside Robotstudio.\n\n"
            f"Goal: {goal}\n\n"
            "Work in this order:\n"
            "1. Call studio_search_keywords for each capability the suite needs and "
            "studio_describe_keyword on the best candidates.\n"
            "2. Draft a canvas document: settings.libraries, settings.variables, "
            "tests with steps, and keywords for shared logic.\n"
            "3. Call studio_preview, then studio_validate with dry_run_check=true.\n"
            "4. Fix every error, then studio_save_suite.\n"
            "5. Call studio_run_suite and report the results.\n"
        )

    @mcp.prompt()
    def debug_failed_run(run_id: str) -> str:
        """Investigate a failed run and propose a fix."""
        try:
            summary = load_run(_workspace(), run_id)
            payload = summary.model_dump_json(indent=2)
        except RunError as error:
            payload = f"(run unavailable: {error})"
        return (
            "A Robotstudio run failed. Here is the summary:\n\n"
            f"{payload}\n\n"
            "Use studio_get_suite on the suite, studio_describe_keyword on any "
            "keyword in the failing steps, then propose a minimal document change. "
            "Validate with studio_validate(dry_run_check=true) before saving."
        )

    return mcp


def _validation_payload(result: Any) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "test_count": result.test_count,
        "messages": [
            {"level": message.level, "message": message.message}
            for message in result.messages
        ],
    }


def main(workspace: str | None = None) -> None:
    """Run the MCP server over stdio."""
    if workspace:
        os.environ["ROBOTSTUDIO_WORKSPACE"] = str(
            Path(workspace).expanduser().resolve()
        )
    server = create_server()
    server.run(transport="stdio")


def version() -> str:
    """Return the Robotstudio version served by this module."""
    return __version__


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
