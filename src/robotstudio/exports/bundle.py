"""Portable run bundles with redaction of secrets."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from robotstudio.exports.junit import build_junit
from robotstudio.exports.tabular import results_csv, results_json
from robotstudio.model.results import RunSummary

DEFAULT_REDACTIONS: tuple[tuple[str, str], ...] = (
    (
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|authorization)"
        r"(\s*[:=]\s*)\S+",
        r"\1\2***",
    ),
    (r"(?i)\b([a-z]+://[^/\s:@]+):[^/\s@]+@", r"\1:***@"),
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "***@***"),
)

_TEXT_SUFFIXES = {
    ".txt",
    ".json",
    ".xml",
    ".csv",
    ".robot",
    ".log",
    ".html",
    ".yaml",
    ".yml",
}


def redact_text(text: str, patterns: tuple[str, ...] = ()) -> str:
    """Remove common secret shapes, plus any caller-supplied regexes."""
    for pattern, replacement in DEFAULT_REDACTIONS:
        text = re.sub(pattern, replacement, text)
    for pattern in patterns:
        text = re.sub(pattern, "***", text)
    return text


def build_bundle(
    summary: RunSummary,
    workspace_root: Path,
    destination: Path,
    redact_patterns: tuple[str, ...] = (),
) -> Path:
    """Write a zip bundle containing sources, results and Robot artifacts."""
    run_dir = Path(summary.output_dir)
    robot_dir = run_dir / "robot"
    destination.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": summary.run_id,
        "suite": summary.stem,
        "status": summary.status,
        "started_at": summary.started_at,
        "finished_at": summary.finished_at,
        "totals": {
            "tests": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "skipped": summary.skipped,
        },
        "redacted": True,
        "redaction_patterns": list(redact_patterns),
    }

    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        _write_text(archive, "manifest.json", json.dumps(manifest, indent=2))
        _write_text(archive, "results/junit.xml", build_junit(summary))
        _write_text(archive, "results/results.csv", results_csv(summary))
        _write_text(archive, "results/results.json", results_json(summary))
        _write_text(archive, "sources/README.txt", _readme(summary))

        for name, path in (
            ("sources/suite.robot", workspace_root / f"{summary.stem}.robot"),
            (
                "sources/suite.canvas.json",
                workspace_root / f"{summary.stem}.canvas.json",
            ),
        ):
            if path.is_file():
                _write_text(
                    archive,
                    name,
                    redact_text(path.read_text(encoding="utf-8"), redact_patterns),
                )

        if robot_dir.is_dir():
            for path in sorted(robot_dir.iterdir()):
                if path.is_file():
                    _write_file(archive, f"robot/{path.name}", path, redact_patterns)

    return destination


def _write_text(archive: zipfile.ZipFile, name: str, text: str) -> None:
    archive.writestr(name, text)


def _write_file(
    archive: zipfile.ZipFile,
    name: str,
    path: Path,
    redact_patterns: tuple[str, ...],
) -> None:
    if path.suffix.lower() in _TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
        archive.writestr(name, redact_text(text, redact_patterns))
    else:
        archive.write(path, name)


def _readme(summary: RunSummary) -> str:
    return (
        f"Robotstudio run bundle\n"
        f"======================\n\n"
        f"Suite: {summary.stem}\n"
        f"Run: {summary.run_id}\n"
        f"Status: {summary.status}\n"
        f"Tests: {summary.total} ({summary.passed} passed, {summary.failed} failed, "
        f"{summary.skipped} skipped)\n"
        f"Started: {summary.started_at}\n"
        f"Finished: {summary.finished_at}\n\n"
        f"JUnit XML lives in results/junit.xml for CI dashboards.\n"
        f"Raw Robot artifacts live in robot/.\n"
        f"Text artifacts have been passed through redaction filters.\n"
    )
