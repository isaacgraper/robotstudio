"""Render a canvas document as Robot Framework source."""

from __future__ import annotations

import re
from collections.abc import Iterable

from robotstudio.model.canvas import (
    Argument,
    CallStep,
    CanvasDocument,
    ForStep,
    IfStep,
    KeywordDefinition,
    KeywordRef,
    ReturnStep,
    SuiteSettings,
    TestCase,
    TryStep,
    VarStep,
    WhileStep,
)

INDENT = "    "
_EMPTY = "${EMPTY}"
_SPACE_RUN = re.compile(r" {2,}")
_TWO_SPACES = "  "


def escape_cell(value: str) -> str:
    """Escape a value so Robot reads it as a single cell."""
    if value == "":
        return _EMPTY
    if (
        _TWO_SPACES not in value
        and not value.startswith(" ")
        and not value.endswith(" ")
    ):
        return value
    escaped = _SPACE_RUN.sub(lambda match: "\\ " * len(match.group(0)), value)
    if escaped.startswith(" "):
        escaped = "\\" + escaped
    if escaped.endswith(" ") and not escaped.endswith("\\ "):
        escaped = escaped[:-1] + "\\ "
    return escaped


def _variable(name: str) -> str:
    """Normalise a variable name to ``${name}`` form."""
    if name.startswith("${") or name.startswith("@{") or name.startswith("&{"):
        return name
    return "${" + name + "}"


def _documentation(text: str) -> str:
    """Collapse a multi-line documentation string into one Robot cell."""
    return escape_cell(text.replace("\r\n", "\n").replace("\n", "\\n"))


def _render_call(step: CallStep, level: int) -> list[str]:
    cells: list[str] = []
    if step.assign:
        names = [_variable(name) for name in step.assign]
        names[-1] = names[-1] + " ="
        cells.append("    ".join(names))
    cells.append(escape_cell(_keyword_name(step.keyword)))
    cells.extend(_render_argument(argument) for argument in step.args)
    lines = [INDENT * level + "    ".join(cells)]
    if step.comment:
        lines[0] += INDENT + "# " + step.comment
    return lines


def _keyword_name(keyword: KeywordRef) -> str:
    """Resolve embedded arguments into the callable keyword name."""
    name = keyword.name
    if not keyword.embedded:
        return name
    for key, value in keyword.embedded.items():
        name = name.replace("${" + key + "}", value)
    return name


def _render_argument(argument: Argument) -> str:
    value = escape_cell(argument.value)
    if argument.name:
        return f"{argument.name}={value}"
    return value


def _render_if(step: IfStep, level: int) -> list[str]:
    pad = INDENT * level
    lines = [pad + "IF    " + escape_cell(step.condition)]
    lines.extend(_render_steps(step.steps, level + 1))
    for branch in step.branches:
        lines.append(pad + "ELSE IF    " + escape_cell(branch.condition))
        lines.extend(_render_steps(branch.steps, level + 1))
    if step.else_steps:
        lines.append(pad + "ELSE")
        lines.extend(_render_steps(step.else_steps, level + 1))
    lines.append(pad + "END")
    return lines


def _render_for(step: ForStep, level: int) -> list[str]:
    pad = INDENT * level
    cells = ["FOR"]
    cells.extend(_variable(name) for name in step.variables)
    cells.append(
        {
            "in": "IN",
            "in_range": "IN RANGE",
            "in_enumerate": "IN ENUMERATE",
            "in_zip": "IN ZIP",
        }[step.flavor]
    )
    cells.extend(escape_cell(value) for value in step.values)
    lines = [pad + "    ".join(cells)]
    lines.extend(_render_steps(step.steps, level + 1))
    lines.append(pad + "END")
    return lines


def _render_while(step: WhileStep, level: int) -> list[str]:
    pad = INDENT * level
    condition = step.condition if not step.until else f"not ({step.condition})"
    cells = ["WHILE", escape_cell(condition)]
    if step.limit:
        cells.append(f"limit={escape_cell(step.limit)}")
    lines = [pad + "    ".join(cells)]
    lines.extend(_render_steps(step.steps, level + 1))
    lines.append(pad + "END")
    return lines


def _render_try(step: TryStep, level: int) -> list[str]:
    pad = INDENT * level
    lines = [pad + "TRY"]
    lines.extend(_render_steps(step.steps, level + 1))
    for clause in step.excepts:
        cells = ["EXCEPT"]
        cells.extend(escape_cell(pattern) for pattern in clause.patterns)
        if clause.variable:
            cells.extend(["AS", _variable(clause.variable)])
        lines.append(pad + "    ".join(cells))
        lines.extend(_render_steps(clause.steps, level + 1))
    if step.else_steps:
        lines.append(pad + "ELSE")
        lines.extend(_render_steps(step.else_steps, level + 1))
    if step.finally_steps:
        lines.append(pad + "FINALLY")
        lines.extend(_render_steps(step.finally_steps, level + 1))
    lines.append(pad + "END")
    return lines


def _render_var(step: VarStep, level: int) -> list[str]:
    cells = ["VAR", _variable(step.name), escape_cell(step.value)]
    if step.scope:
        cells.append(f"scope={step.scope.upper()}")
    return [INDENT * level + "    ".join(cells)]


def _render_return(step: ReturnStep, level: int) -> list[str]:
    cells = ["RETURN"]
    cells.extend(escape_cell(value) for value in step.values)
    return [INDENT * level + "    ".join(cells)]


def _render_steps(steps: Iterable[object], level: int) -> list[str]:
    """Render a list of heterogeneous steps at ``level`` indentation."""
    from robotstudio.model.canvas import (
        BreakStep,
        CommentStep,
        ContinueStep,
        RawStep,
    )

    lines: list[str] = []
    for step in steps:
        if isinstance(step, CallStep):
            lines.extend(_render_call(step, level))
        elif isinstance(step, IfStep):
            lines.extend(_render_if(step, level))
        elif isinstance(step, ForStep):
            lines.extend(_render_for(step, level))
        elif isinstance(step, WhileStep):
            lines.extend(_render_while(step, level))
        elif isinstance(step, TryStep):
            lines.extend(_render_try(step, level))
        elif isinstance(step, VarStep):
            lines.extend(_render_var(step, level))
        elif isinstance(step, ReturnStep):
            lines.extend(_render_return(step, level))
        elif isinstance(step, BreakStep):
            lines.append(INDENT * level + "BREAK")
        elif isinstance(step, ContinueStep):
            lines.append(INDENT * level + "CONTINUE")
        elif isinstance(step, CommentStep):
            text = step.text if step.text.startswith("#") else "# " + step.text
            lines.append(INDENT * level + text)
        elif isinstance(step, RawStep):
            lines.extend(INDENT * level + line for line in step.lines)
        else:  # pragma: no cover - defensive
            raise TypeError(f"Unsupported step: {type(step)!r}")
    return lines


def _render_import_header(settings: SuiteSettings) -> list[str]:
    lines: list[str] = []
    if settings.documentation:
        lines.append("Documentation    " + _documentation(settings.documentation))
    for library in settings.libraries:
        cells = ["Library", escape_cell(library.name)]
        cells.extend(escape_cell(argument) for argument in library.args)
        if library.alias:
            cells.extend(["AS", escape_cell(library.alias)])
        lines.append("    ".join(cells))
    for resource in settings.resources:
        lines.append("Resource    " + escape_cell(resource.path))
    if settings.suite_setup:
        lines.append(_render_slot("Suite Setup", settings.suite_setup))
    if settings.suite_teardown:
        lines.append(_render_slot("Suite Teardown", settings.suite_teardown))
    if settings.test_setup:
        lines.append(_render_slot("Test Setup", settings.test_setup))
    if settings.test_teardown:
        lines.append(_render_slot("Test Teardown", settings.test_teardown))
    if settings.force_tags:
        cells = ["Force Tags"]
        cells.extend(map(escape_cell, settings.force_tags))
        lines.append("    ".join(cells))
    if settings.default_tags:
        cells = ["Default Tags"]
        cells.extend(map(escape_cell, settings.default_tags))
        lines.append("    ".join(cells))
    if settings.test_timeout:
        lines.append("Test Timeout    " + escape_cell(settings.test_timeout))
    for key, value in settings.metadata.items():
        lines.append(f"Metadata    {escape_cell(key)}    {escape_cell(value)}")
    return lines


def _render_slot(label: str, step: CallStep) -> str:
    """Render a setup or teardown call in a settings-like slot."""
    cells = [label, escape_cell(_keyword_name(step.keyword))]
    cells.extend(_render_argument(argument) for argument in step.args)
    return "    ".join(cells)


def _render_variables(settings: SuiteSettings) -> list[str]:
    return [
        _variable(variable.name) + "    " + escape_cell(variable.value)
        for variable in settings.variables
    ]


def _render_test(test: TestCase) -> list[str]:
    lines = [escape_cell(test.name)]
    if test.documentation:
        lines.append(
            INDENT + "[Documentation]    " + _documentation(test.documentation)
        )
    if test.tags:
        cells = ["[Tags]"]
        cells.extend(map(escape_cell, test.tags))
        lines.append(INDENT + "    ".join(cells))
    if test.setup:
        lines.append(INDENT + _render_slot("[Setup]", test.setup))
    if test.teardown:
        lines.append(INDENT + _render_slot("[Teardown]", test.teardown))
    if test.timeout:
        lines.append(INDENT + "[Timeout]    " + escape_cell(test.timeout))
    if test.template:
        lines.append(INDENT + "[Template]    " + escape_cell(test.template))
    lines.extend(_render_steps(test.steps, 1))
    return lines


def _render_keyword(keyword: KeywordDefinition) -> list[str]:
    lines = [escape_cell(keyword.name)]
    if keyword.arguments:
        cells = ["[Arguments]"]
        cells.extend(escape_cell(argument) for argument in keyword.arguments)
        lines.append(INDENT + "    ".join(cells))
    if keyword.documentation:
        lines.append(
            INDENT + "[Documentation]    " + _documentation(keyword.documentation)
        )
    if keyword.tags:
        cells = ["[Tags]"]
        cells.extend(map(escape_cell, keyword.tags))
        lines.append(INDENT + "    ".join(cells))
    if keyword.teardown:
        lines.append(INDENT + _render_slot("[Teardown]", keyword.teardown))
    lines.extend(_render_steps(keyword.steps, 1))
    return lines


def _section(title: str, body: list[str]) -> list[str]:
    if not body:
        return []
    return [f"*** {title} ***", *body, ""]


def write_document(document: CanvasDocument) -> str:
    """Render ``document`` as a complete Robot Framework suite."""
    lines: list[str] = []
    lines.extend(_section("Settings", _render_import_header(document.settings)))
    lines.extend(_section("Variables", _render_variables(document.settings)))

    test_body: list[str] = []
    for test in document.tests:
        test_body.extend(_render_test(test))
        test_body.append("")
    lines.extend(_section("Test Cases", test_body))

    keyword_body: list[str] = []
    for keyword in document.keywords:
        keyword_body.extend(_render_keyword(keyword))
        keyword_body.append("")
    lines.extend(_section("Keywords", keyword_body))

    return "\n".join(lines).rstrip("\n") + "\n"
