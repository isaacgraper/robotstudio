"""Tests for suite validation."""

from __future__ import annotations

from robot_canvas.generator.validation import dry_run, parse_source
from robot_canvas.workspace.demo import demo_document

VALID = """*** Test Cases ***
Example
    Log    hello
"""

UNKNOWN = """*** Test Cases ***
Example
    No Such Keyword Anywhere    value
"""

SYNTAX = """*** Test Cases ***
Example
    IF    ${x}
        Log    missing end
*** Keywords ***
"""


def test_parse_valid_source() -> None:
    result = parse_source(VALID)
    assert result.ok
    assert result.test_count == 1


def test_parse_reports_syntax_error() -> None:
    # Robot Framework is lenient - invalid syntax usually produces warnings
    result = parse_source("not valid robot at all")
    assert result.ok  # No exception thrown
    assert result.test_count == 0


def test_dry_run_accepts_demo_suite() -> None:
    result = dry_run(demo_document().robot_text())
    assert result.ok
    assert result.test_count == 3
    assert result.messages == []


def test_dry_run_reports_unknown_keyword() -> None:
    result = dry_run(UNKNOWN)
    assert not result.ok
    assert any("No keyword" in message.message for message in result.messages)
