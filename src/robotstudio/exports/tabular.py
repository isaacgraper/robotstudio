"""CSV and JSON exports for test cases and run results."""

from __future__ import annotations

import csv
import io
from typing import Any

from robotstudio.model.canvas import CanvasDocument
from robotstudio.model.results import RunSummary


def cases_csv(document: CanvasDocument) -> str:
    """Render the authored test cases as CSV."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        ["suite", "test", "documentation", "tags", "steps", "setup", "teardown"]
    )
    for test in document.tests:
        writer.writerow(
            [
                document.name,
                test.name,
                test.documentation,
                " ".join(test.tags),
                _count_steps(test.steps),
                test.setup.keyword.name if test.setup else "",
                test.teardown.keyword.name if test.teardown else "",
            ]
        )
    return buffer.getvalue()


def results_csv(summary: RunSummary) -> str:
    """Render run results as CSV, one row per test case."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "suite",
            "test",
            "status",
            "elapsed_ms",
            "tags",
            "message",
        ]
    )
    for case in summary.cases:
        writer.writerow(
            [
                summary.run_id,
                case.suite,
                case.name,
                case.status,
                case.elapsed_ms,
                " ".join(case.tags),
                case.message,
            ]
        )
    return buffer.getvalue()


def results_json(summary: RunSummary) -> str:
    """Render the run summary as indented JSON."""
    return summary.model_dump_json(indent=2) + "\n"


def _count_steps(steps: list[Any]) -> int:
    total = 0
    for step in steps:
        total += 1
        nested = getattr(step, "steps", None)
        if isinstance(nested, list):
            total += _count_steps(nested)
        for attribute in ("else_steps", "finally_steps"):
            branch = getattr(step, attribute, None)
            if isinstance(branch, list):
                total += _count_steps(branch)
        for branch in getattr(step, "branches", []) or []:
            total += 1 + _count_steps(getattr(branch, "steps", []))
        for clause in getattr(step, "excepts", []) or []:
            total += 1 + _count_steps(getattr(clause, "steps", []))
    return total
