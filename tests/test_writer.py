"""Tests for the Robot source generator."""

from __future__ import annotations

from pathlib import Path

from robotstudio.generator.writer import escape_cell, write_document
from robotstudio.model.canvas import (
    Argument,
    BreakStep,
    CallStep,
    CanvasDocument,
    CommentStep,
    ContinueStep,
    ExceptClause,
    ForStep,
    IfStep,
    KeywordDefinition,
    KeywordRef,
    LibraryImport,
    RawStep,
    ResourceImport,
    ReturnStep,
    SuiteSettings,
    TestCase,
    TryStep,
    Variable,
    VarStep,
    WhileStep,
)
from robotstudio.workspace.demo import demo_document

GOLDEN = Path(__file__).parent / "golden" / "demo.robot"


def _call(name: str, *values: str, assign: list[str] | None = None) -> CallStep:
    return CallStep(
        keyword=KeywordRef(name=name),
        args=[Argument(value=value) for value in values],
        assign=assign or [],
    )


def test_escape_keeps_single_spaces() -> None:
    assert escape_cell("hello world") == "hello world"


def test_escape_protects_double_spaces() -> None:
    assert escape_cell("hello  world") == "hello\\ \\ world"


def test_escape_replaces_empty_values() -> None:
    assert escape_cell("") == "${EMPTY}"


def test_demo_matches_golden_file() -> None:
    assert demo_document().robot_text() == GOLDEN.read_text(encoding="utf-8")


def test_settings_and_slots_are_rendered() -> None:
    document = CanvasDocument(
        name="Settings",
        settings=SuiteSettings(
            documentation="Line one\nLine two",
            libraries=[LibraryImport(name="Collections", alias="Col")],
            resources=[ResourceImport(path="common.resource")],
            variables=[Variable(name="PORT", value="8080")],
            suite_setup=_call("Log", "start"),
            suite_teardown=_call("Log", "stop"),
            test_setup=_call("Log", "test start"),
            test_teardown=_call("Log", "test stop"),
            force_tags=["smoke"],
            default_tags=["default"],
            test_timeout="1 min",
            metadata={"Owner": "team"},
        ),
    )
    source = write_document(document)
    assert "Documentation    Line one\\nLine two" in source
    assert "Library    Collections    AS    Col" in source
    assert "Resource    common.resource" in source
    assert "${PORT}    8080" in source
    assert "Suite Setup    Log    start" in source
    assert "Suite Teardown    Log    stop" in source
    assert "Test Setup    Log    test start" in source
    assert "Test Teardown    Log    test stop" in source
    assert "Force Tags    smoke" in source
    assert "Default Tags    default" in source
    assert "Test Timeout    1 min" in source
    assert "Metadata    Owner    team" in source


def test_test_case_metadata_is_rendered() -> None:
    document = CanvasDocument(
        name="Metadata",
        tests=[
            TestCase(
                name="One Test",
                documentation="doc",
                tags=["a", "b"],
                setup=_call("Log", "setup"),
                teardown=_call("Log", "teardown"),
                timeout="10s",
                template="Some Template",
            )
        ],
    )
    source = write_document(document)
    assert "[Documentation]    doc" in source
    assert "[Tags]    a    b" in source
    assert "[Setup]    Log    setup" in source
    assert "[Teardown]    Log    teardown" in source
    assert "[Timeout]    10s" in source
    assert "[Template]    Some Template" in source


def test_call_assignments_and_named_arguments() -> None:
    step = CallStep(
        keyword=KeywordRef(name="Create Dictionary"),
        args=[
            Argument(value="@{items}"),
            Argument(name="scope", value="SUITE"),
            Argument(value="hello  world"),
        ],
        assign=["first", "second"],
        comment="explain",
    )
    source = write_document(
        CanvasDocument(name="Calls", tests=[TestCase(name="T", steps=[step])])
    )
    assert "${first}    ${second} =    Create Dictionary" in source
    assert "scope=SUITE" in source
    assert "hello\\ \\ world" in source
    assert "# explain" in source


def test_embedded_arguments_are_resolved() -> None:
    step = CallStep(
        keyword=KeywordRef(
            name='Call "${service}" Method "${method}"',
            embedded={"service": "power", "method": "on"},
        )
    )
    source = write_document(
        CanvasDocument(name="Embedded", tests=[TestCase(name="T", steps=[step])])
    )
    assert 'Call "power" Method "on"' in source
    assert "${service}" not in source


def test_control_flow_is_nested() -> None:
    steps = [
        IfStep(
            condition="${x} > 1",
            steps=[_call("Log", "big")],
            branches=[IfStep(condition="${x} == 1", steps=[_call("Log", "one")])],
            else_steps=[_call("Log", "small")],
        ),
        ForStep(
            variables=["item"],
            values=["a", "b"],
            steps=[_call("Log", "${item}")],
        ),
        ForStep(
            variables=["index"],
            values=["1", "10"],
            flavor="in_range",
            steps=[_call("Log", "${index}")],
        ),
        WhileStep(
            condition="${x} < 10",
            limit="10s",
            steps=[_call("Evaluate", "${x} + 1")],
        ),
        WhileStep(condition="${ready}", until=True, steps=[_call("Sleep", "1s")]),
        TryStep(
            steps=[_call("Fail", "boom")],
            excepts=[
                ExceptClause(
                    patterns=["boom"],
                    variable="error",
                    steps=[_call("Log", "${error}")],
                )
            ],
            else_steps=[_call("Log", "no failure")],
            finally_steps=[_call("Log", "done")],
        ),
    ]
    source = write_document(
        CanvasDocument(name="Flow", tests=[TestCase(name="T", steps=steps)])
    )
    assert "IF    ${x} > 1" in source
    assert "ELSE IF    ${x} == 1" in source
    assert "ELSE\n        Log    small" in source
    assert "FOR    ${item}    IN    a    b" in source
    assert "FOR    ${index}    IN RANGE    1    10" in source
    assert "WHILE    ${x} < 10    limit=10s" in source
    assert "WHILE    not (${ready})" in source
    assert "EXCEPT    boom    AS    ${error}" in source
    assert "FINALLY" in source
    assert source.count("END") == 6


def test_statements_and_raw_lines() -> None:
    steps = [
        VarStep(name="count", value="1", scope="suite"),
        ReturnStep(values=["${count}"]),
        BreakStep(),
        ContinueStep(),
        CommentStep(text="note"),
        CommentStep(text="# already a comment"),
        RawStep(lines=["Custom Syntax    value"]),
    ]
    source = write_document(
        CanvasDocument(
            name="Statements",
            tests=[TestCase(name="T", steps=steps)],
        )
    )
    assert "VAR    ${count}    1    scope=SUITE" in source
    assert "RETURN    ${count}" in source
    assert "BREAK" in source
    assert "CONTINUE" in source
    assert "# note" in source
    assert "# already a comment" in source
    assert "Custom Syntax    value" in source


def test_keyword_definition_renders_header() -> None:
    keyword = KeywordDefinition(
        name="Do Work",
        arguments=["${one}", "${two}=2"],
        documentation="Work.",
        tags=["helper"],
        teardown=_call("Log", "bye"),
        steps=[_call("Log", "${one}")],
    )
    source = write_document(CanvasDocument(name="Kw", keywords=[keyword]))
    assert "*** Keywords ***" in source
    assert "Do Work" in source
    assert "[Arguments]    ${one}    ${two}=2" in source
    assert "[Tags]    helper" in source
    assert "[Teardown]    Log    bye" in source


def test_section_order() -> None:
    source = write_document(demo_document())
    assert source.index("*** Settings ***") < source.index("*** Variables ***")
    assert source.index("*** Variables ***") < source.index("*** Test Cases ***")
    assert source.index("*** Test Cases ***") < source.index("*** Keywords ***")
    assert source.endswith("\n")
