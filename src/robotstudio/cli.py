"""Command line interface for Robotstudio."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from robotstudio import __version__
from robotstudio.generator.validation import dry_run, parse_source
from robotstudio.keywords.catalog import load_catalog
from robotstudio.model.canvas import CanvasDocument
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import Workspace, WorkspaceError


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser."""
    parser = argparse.ArgumentParser(
        prog="robotstudio",
        description="Visual authoring and execution for Robot Framework.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Start the web application.")
    serve.add_argument(
        "--workspace",
        default=os.environ.get("ROBOTSTUDIO_WORKSPACE", "workspace"),
        help="Directory holding canvas documents and suites.",
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    init = commands.add_parser("init", help="Create a workspace with a demo suite.")
    init.add_argument(
        "--workspace",
        default=os.environ.get("ROBOTSTUDIO_WORKSPACE", "workspace"),
        help="Directory to create.",
    )
    init.add_argument("--force", action="store_true", help="Overwrite the demo suite.")

    generate = commands.add_parser(
        "generate", help="Render a canvas JSON document as Robot source."
    )
    generate.add_argument("document", type=Path)
    generate.add_argument("--out", type=Path, default=None)

    validate = commands.add_parser(
        "validate", help="Parse a canvas document and optionally dry-run it."
    )
    validate.add_argument("document", type=Path)
    validate.add_argument("--dry-run", action="store_true")

    catalog = commands.add_parser("catalog", help="Print the keyword catalog.")
    catalog.add_argument("--library", action="append", default=[])
    catalog.add_argument("--curated", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested command."""
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "serve":
            return _serve(arguments)
        if arguments.command == "init":
            return _init(arguments)
        if arguments.command == "generate":
            return _generate(arguments)
        if arguments.command == "validate":
            return _validate(arguments)
        if arguments.command == "catalog":
            return _catalog(arguments)
    except WorkspaceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 1


def _serve(arguments: argparse.Namespace) -> int:
    import uvicorn

    os.environ["ROBOTSTUDIO_WORKSPACE"] = str(Path(arguments.workspace))
    print(f"Robotstudio {__version__} on http://{arguments.host}:{arguments.port}")
    print(f"Workspace: {Path(arguments.workspace).resolve()}")
    if arguments.reload:
        uvicorn.run(
            "robotstudio.api.app:create_app",
            factory=True,
            host=arguments.host,
            port=arguments.port,
            reload=True,
        )
    else:
        from robotstudio.api.app import create_app

        uvicorn.run(
            create_app(arguments.workspace),
            host=arguments.host,
            port=arguments.port,
        )
    return 0


def _init(arguments: argparse.Namespace) -> int:
    workspace = Workspace(arguments.workspace)
    stem = "robotstudio-demo"
    if workspace.canvas_path(stem).exists() and not arguments.force:
        print(f"Demo suite already exists: {workspace.canvas_path(stem)}")
        return 0
    saved = workspace.save(demo_document(), stem)
    validation = parse_source(saved.robot_text)
    print(f"Created {saved.canvas_path}")
    print(f"Created {saved.robot_path}")
    print(f"Validation: {'ok' if validation.ok else 'failed'}")
    return 0


def _generate(arguments: argparse.Namespace) -> int:
    document = CanvasDocument.model_validate_json(
        arguments.document.read_text(encoding="utf-8")
    )
    source = document.robot_text()
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(source, encoding="utf-8", newline="\n")
        print(f"Wrote {arguments.out}")
    else:
        sys.stdout.write(source)
    return 0


def _validate(arguments: argparse.Namespace) -> int:
    document = CanvasDocument.model_validate_json(
        arguments.document.read_text(encoding="utf-8")
    )
    source = document.robot_text()
    if arguments.dry_run:
        result = dry_run(source, arguments.document.parent)
    else:
        result = parse_source(source)
    print(f"Tests: {result.test_count}")
    print(f"Status: {'ok' if result.ok else 'failed'}")
    for message in result.messages:
        print(f"  {message.level}: {message.message}")
    return 0 if result.ok else 1


def _catalog(arguments: argparse.Namespace) -> int:
    catalog = load_catalog(arguments.library or None)
    keywords = catalog.curated_keywords if arguments.curated else catalog.keywords
    for keyword in keywords:
        print(f"{keyword.category:<10} {keyword.name:<45} {keyword.library}")
    print(f"\n{len(keywords)} keywords from {len(catalog.libraries)} libraries")
    for failure in catalog.failures:
        print(f"  unavailable: {failure.name}: {failure.error}", file=sys.stderr)
    return 0
