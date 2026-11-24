"""Run Robot Framework suites and export their results."""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404 - suites are executed in a controlled workspace
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from robot.api import ExecutionResult

from robotstudio.exports.bundle import build_bundle
from robotstudio.exports.junit import build_junit
from robotstudio.exports.tabular import cases_csv, results_csv, results_json
from robotstudio.model.results import CaseResult, RunStatus, RunSummary
from robotstudio.workspace.store import Workspace, WorkspaceError

RUNS_DIR = ".runs"
DEFAULT_TIMEOUT = 600.0
SUMMARY_NAME = "summary.json"
EXPORT_FORMATS = {
    "junit": "junit.xml",
    "results-csv": "results.csv",
    "cases-csv": "cases.csv",
    "results-json": "results.json",
    "bundle": "bundle.zip",
}

_ACTIVE = threading.Lock()


class RunError(Exception):
    """Raised when a suite cannot be executed."""


class RunBusyError(RunError):
    """Raised when a run is already in progress."""


def run_suite(
    workspace: Workspace,
    stem: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    redact_patterns: tuple[str, ...] = (),
) -> RunSummary:
    """Execute a stored suite and record its results."""
    try:
        document = workspace.load(stem)
    except WorkspaceError as error:
        raise RunError(str(error)) from error
    saved = workspace.save(document, stem)

    if not _ACTIVE.acquire(blocking=False):
        raise RunBusyError("Another run is already in progress")
    try:
        return _execute(workspace, stem, saved.robot_path, timeout)
    finally:
        _ACTIVE.release()


def _execute(
    workspace: Workspace,
    stem: str,
    robot_path: Path,
    timeout: float,
) -> RunSummary:
    started = datetime.now(UTC)
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    run_dir = runs_root(workspace) / run_id
    robot_dir = run_dir / "robot"
    robot_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "robot",
        "--outputdir",
        str(robot_dir),
        "--output",
        "output.xml",
        "--log",
        "log.html",
        "--report",
        "report.html",
        "--console",
        "none",
        str(robot_path),
    ]

    status: RunStatus = "passed"
    error: str | None = None
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, local suite path
            command,
            cwd=str(workspace.root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        console = (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as expired:
        status = "timeout"
        error = f"Run exceeded the {timeout:.0f}s timeout"
        console = str(expired)
    except OSError as failure:
        status = "error"
        error = f"Could not start Robot Framework: {failure}"
        console = str(failure)

    (run_dir / "console.log").write_text(console, encoding="utf-8", newline="\n")

    cases: list[CaseResult] = []
    output_xml = robot_dir / "output.xml"
    if status not in ("timeout", "error") or output_xml.is_file():
        if output_xml.is_file():
            try:
                cases = _collect_cases(output_xml)
            except Exception as failure:  # noqa: BLE001 - surface parser errors as run errors
                status = "error"
                error = f"Could not parse Robot output: {failure}"
        else:
            status = "error"
            error = error or "Robot Framework produced no output.xml"

    passed = sum(1 for case in cases if case.status.upper() == "PASS")
    failed = sum(1 for case in cases if case.status.upper() == "FAIL")
    skipped = len(cases) - passed - failed
    if failed:
        status = "failed"
    elif status == "passed" and not cases:
        status = "error"
        error = error or "No test cases were executed"

    finished = datetime.now(UTC)
    summary = RunSummary(
        run_id=run_id,
        stem=stem,
        status=status,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_ms=int((finished - started).total_seconds() * 1000),
        total=len(cases),
        passed=passed,
        failed=failed,
        skipped=skipped,
        cases=cases,
        output_dir=str(run_dir),
        error=error,
    )

    (run_dir / SUMMARY_NAME).write_text(
        summary.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return summary


def _collect_cases(output_xml: Path) -> list[CaseResult]:
    result = ExecutionResult(str(output_xml))
    cases: list[CaseResult] = []

    def visit(suite: object) -> None:
        for test in getattr(suite, "tests", []):
            cases.append(
                CaseResult(
                    name=str(getattr(test, "name", "")),
                    suite=str(getattr(suite, "name", "")),
                    status=str(getattr(test, "status", "UNKNOWN")),
                    message=str(getattr(test, "message", "") or ""),
                    elapsed_ms=int(getattr(test, "elapsedtime", 0) or 0),
                    tags=[str(tag) for tag in getattr(test, "tags", [])],
                )
            )
        for child in getattr(suite, "suites", []):
            visit(child)

    visit(result.suite)
    return cases


def runs_root(workspace: Workspace) -> Path:
    """Return the directory that holds run output."""
    return workspace.root / RUNS_DIR


def list_runs(workspace: Workspace, limit: int = 50) -> list[RunSummary]:
    """List stored runs, newest first."""
    root = runs_root(workspace)
    if not root.is_dir():
        return []
    summaries: list[RunSummary] = []
    for path in root.glob(f"*/{SUMMARY_NAME}"):
        try:
            summaries.append(RunSummary.model_validate_json(path.read_text("utf-8")))
        except (OSError, ValueError):
            continue
    summaries.sort(key=lambda item: item.started_at, reverse=True)
    return summaries[:limit]


def load_run(workspace: Workspace, run_id: str) -> RunSummary:
    """Load one recorded run by id."""
    path = runs_root(workspace) / run_id / SUMMARY_NAME
    if not path.is_file():
        raise RunError(f"Run not found: {run_id}")
    return RunSummary.model_validate_json(path.read_text(encoding="utf-8"))


def export_run(
    workspace: Workspace,
    run_id: str,
    export: str,
    redact_patterns: tuple[str, ...] = (),
) -> tuple[Path, str]:
    """Write an export artifact for a run and return its path and media type."""
    if export not in EXPORT_FORMATS:
        raise RunError(f"Unknown export format: {export}")
    summary = load_run(workspace, run_id)
    run_dir = Path(summary.output_dir)
    target = run_dir / EXPORT_FORMATS[export]

    if export == "junit":
        target.write_text(build_junit(summary), encoding="utf-8", newline="\n")
    elif export == "results-csv":
        target.write_text(results_csv(summary), encoding="utf-8", newline="\n")
    elif export == "results-json":
        target.write_text(results_json(summary), encoding="utf-8", newline="\n")
    elif export == "cases-csv":
        target.write_text(
            cases_csv(workspace.load(summary.stem)), encoding="utf-8", newline="\n"
        )
    else:
        staging = run_dir / "sources"
        if staging.exists():
            shutil.rmtree(staging)
        build_bundle(summary, workspace.root, target, redact_patterns)

    return target, _media_type(export)


def _media_type(export: str) -> str:
    if export == "junit":
        return "application/xml"
    if export == "results-json":
        return "application/json"
    if export == "bundle":
        return "application/zip"
    return "text/csv"
