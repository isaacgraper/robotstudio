"""Validation of generated Robot Framework source."""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path

from robot.api import TestSuite
from robot.errors import DataError, Information
from robot.result.model import TestSuite as ResultTestSuite
from robot.running.model import TestCase as RobotTestCase


@dataclass(slots=True)
class ValidationMessage:
    """One problem found while validating a suite."""

    level: str
    message: str
    line: int | None = None


@dataclass(slots=True)
class ValidationResult:
    """Outcome of parsing and dry-running a suite."""

    ok: bool
    messages: list[ValidationMessage] = field(default_factory=list)
    test_count: int = 0

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""
        return {
            "ok": self.ok,
            "test_count": self.test_count,
            "messages": [
                {"level": item.level, "message": item.message, "line": item.line}
                for item in self.messages
            ],
        }


def parse_source(source: str) -> ValidationResult:
    """Parse Robot source without executing it."""
    try:
        suite = TestSuite.from_string(source)
    except (DataError, Information) as error:
        return ValidationResult(
            ok=False,
            messages=[ValidationMessage(level="error", message=str(error))],
        )
    return ValidationResult(ok=True, test_count=_count_tests(suite))


def dry_run(source: str, workspace: Path | None = None) -> ValidationResult:
    """Parse the source and resolve every keyword without touching hardware."""
    parsed = parse_source(source)
    if not parsed.ok:
        return parsed
    temp_dir = workspace or Path.cwd()
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / ".robotstudio_dryrun.robot"
    path.write_text(source, encoding="utf-8")
    try:
        suite = TestSuite.from_file_system(path)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = suite.run(dryrun=True, output=None, log=None, report=None)
    except (DataError, Information) as error:
        return ValidationResult(
            ok=False,
            messages=[ValidationMessage(level="error", message=str(error))],
            test_count=parsed.test_count,
        )
    finally:
        path.unlink(missing_ok=True)
    messages: list[ValidationMessage] = []
    for test in _all_tests(result.suite):
        if test.status == "FAIL":  # type: ignore[attr-defined]
            messages.append(
                ValidationMessage(
                    level="error",
                    message=f"{test.name}: {test.message}",  # type: ignore[attr-defined]
                )
            )
    return ValidationResult(
        ok=not messages,
        messages=messages,
        test_count=parsed.test_count,
    )


def _all_tests(suite: ResultTestSuite) -> list[RobotTestCase]:
    """Return every test in ``suite``, including child suites."""
    found: list[object] = list(getattr(suite, "tests", []) or [])
    for child in getattr(suite, "suites", []) or []:
        found.extend(_all_tests(child))
    return found


def _count_tests(suite: TestSuite) -> int:
    """Count tests recursively without relying on private Robot APIs."""
    count = len(getattr(suite, "tests", []) or [])
    for child in getattr(suite, "suites", []) or []:
        count += _count_tests(child)
    return count
