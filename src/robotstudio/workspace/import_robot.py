"""Import Robot Framework .robot files into canvas model."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from robot.api import get_model
from robot.parsing.model.blocks import (
    Break,
    Continue,
    For,
    If,
    Keyword,
    KeywordCall,
    TestCase,
    Try,
    Var,
    While,
)
from robot.parsing.model.statements import (
    Arguments,
    Comment,
    DefaultTags,
    Documentation,
    EmptyLine,
    Error,
    LibraryImport,
    Metadata,
    ResourceImport,
    Return,
    Setup,
    SuiteSetup,
    SuiteTeardown,
    Tags,
    Teardown,
    Template,
    TemplateArguments,
    TestSetup,
    TestTags,
    TestTeardown,
    TestTimeout,
    Timeout,
    Variable,
)

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
    RawStep,
    ReturnStep,
    Step,
    SuiteSettings,
    TryStep,
    VarStep,
    WhileStep,
)
from robotstudio.model.canvas import (
    LibraryImport as CanvasLibraryImport,
)
from robotstudio.model.canvas import (
    ResourceImport as CanvasResourceImport,
)
from robotstudio.model.canvas import (
    TestCase as CanvasTestCase,
)
from robotstudio.model.canvas import (
    Variable as CanvasVariable,
)

_SOURCE_LINES: list[str] = []


def _set_source_lines(source: str) -> None:
    """Store source lines for variable name extraction."""
    global _SOURCE_LINES
    _SOURCE_LINES = source.splitlines()


def _extract_var_name_from_source(
    lineno: int, col_offset: int, end_lineno: int, end_col_offset: int
) -> str:
    """Extract variable name from original source using line/column info."""
    if not _SOURCE_LINES:
        return ""
    # lineno is 1-based
    line_idx = lineno - 1
    if 0 <= line_idx < len(_SOURCE_LINES):
        line = _SOURCE_LINES[line_idx]
        # Extract from col_offset to end_col_offset
        if end_lineno == lineno:
            segment = line[col_offset:end_col_offset]
        else:
            segment = line[col_offset:]
        # Find ${...}, @{...}, or &{...} pattern
        match = re.search(r"[\$\@\&]\{([^}]+)\}", segment)
        if match:
            return match.group(1)
    return ""


def _token_value(token: Any) -> str:
    """Extract string value from a Robot token."""
    if hasattr(token, "value"):
        return str(token.value)
    if isinstance(token, (list, tuple)) and len(token) > 1:
        return str(token[1])
    return str(token)


def _first_arg_value(tokens: Any) -> str:
    """Extract the first argument value from tokens, skipping separators."""
    arg_value = None
    for token in tokens:
        if hasattr(token, "type") and token.type == "ARGUMENT":
            return str(token.value)
        val = _token_value(token)
        if val.strip() and val not in ("\\",):
            # Store as fallback but continue looking for ARGUMENT token
            if arg_value is None:
                arg_value = val
    # Return ARGUMENT token value if found, otherwise fallback
    return arg_value or ""


def _token_values(tokens: Any) -> list[str]:
    """Extract all values from a token sequence."""
    return [_token_value(t) for t in tokens]


def _values(tokens: Any) -> list[str]:
    """Extract the non-empty, stripped values from a token sequence."""
    values = []
    for token in tokens:
        value = _token_value(token).strip()
        if value:
            values.append(value)
    return values


def _parse_header_condition(header: Any) -> str:
    """Extract condition text from a control structure header."""
    if not header or not hasattr(header, "tokens"):
        return ""
    values = _values(header.tokens)
    if values and values[0] in ("IF", "ELSE IF", "WHILE"):
        values = values[1:]
    return " ".join(value for value in values if not value.startswith("limit="))


def _parse_keyword_call(stmt: Any) -> CallStep:
    """Parse a KeywordCall or TemplateArguments into a CallStep."""
    keyword_name = ""
    args: list[Argument] = []
    assign: list[str] = []
    comment = None

    for token in getattr(stmt, "tokens", []):
        token_type = getattr(token, "type", "")
        value = _token_value(token).strip()
        if not value:
            continue
        if token_type == "ASSIGN":
            name = value[:-1].strip() if value.endswith("=") else value
            if name:
                assign.append(name)
        elif token_type == "KEYWORD":
            keyword_name = value
        elif token_type == "COMMENT":
            comment = value.lstrip("#").strip()
        elif token_type == "ARGUMENT":
            if "=" in value and not value.startswith(("${", "@{", "&{")):
                name, _, arg_value = value.partition("=")
                args.append(Argument(name=name, value=arg_value))
            else:
                args.append(Argument(value=value))
        elif not keyword_name:
            keyword_name = value

    if not keyword_name:
        keyword_name = "Unknown"

    return CallStep(
        keyword=KeywordRef(name=keyword_name),
        args=args,
        assign=assign,
        comment=comment,
    )


def _parse_setup_teardown(stmt: Any) -> CallStep | None:
    """Parse a Setup/Teardown statement."""
    tokens = getattr(getattr(stmt, "header", None), "tokens", None)
    if tokens is None:
        tokens = getattr(stmt, "tokens", [])
    values = _values(tokens)
    if values and values[0] in (
        "Suite Setup",
        "Suite Teardown",
        "Test Setup",
        "Test Teardown",
        "[Setup]",
        "[Teardown]",
    ):
        values = values[1:]
    if not values:
        return None
    return CallStep(
        keyword=KeywordRef(name=values[0]),
        args=[Argument(value=value) for value in values[1:]],
    )


_FOR_FLAVORS: dict[str, Literal["in", "in_range", "in_enumerate", "in_zip"]] = {
    "IN": "in",
    "IN RANGE": "in_range",
    "IN ENUMERATE": "in_enumerate",
    "IN ZIP": "in_zip",
}


def _parse_for_stmt(stmt: For) -> ForStep:
    """Parse a FOR loop."""
    header = getattr(stmt, "header", None)
    variables: list[str] = []
    flavor: Literal["in", "in_range", "in_enumerate", "in_zip"] = "in"
    loop_values: list[str] = []

    if header and hasattr(header, "tokens"):
        for token in header.tokens:
            token_type = getattr(token, "type", "")
            value = _token_value(token).strip()
            if not value:
                continue
            if token_type == "VARIABLE":
                variables.append(value)
            elif token_type == "ARGUMENT":
                loop_values.append(value)
            else:
                normalized = " ".join(value.upper().split())
                if normalized in _FOR_FLAVORS:
                    flavor = _FOR_FLAVORS[normalized]

    steps = _parse_body(stmt.body) if hasattr(stmt, "body") else []

    return ForStep(
        variables=variables,
        values=loop_values,
        flavor=flavor,
        steps=steps,
    )


def _parse_if_stmt(stmt: If) -> IfStep:
    """Parse an IF block."""
    condition = _parse_header_condition(getattr(stmt, "header", None))

    steps = _parse_body(stmt.body) if hasattr(stmt, "body") else []
    branches = []
    else_steps = []

    if hasattr(stmt, "orelse") and stmt.orelse:
        orelse = stmt.orelse
        while orelse:
            branch_condition = getattr(orelse, "condition", None)
            if branch_condition is None:
                # This is an ELSE branch (no condition)
                else_steps = _parse_body(orelse.body) if hasattr(orelse, "body") else []
            else:
                # This is an ELSE IF branch
                branch_cond_text = _parse_header_condition(
                    getattr(orelse, "header", None)
                )
                branch_steps = (
                    _parse_body(orelse.body) if hasattr(orelse, "body") else []
                )
                branches.append(IfStep(condition=branch_cond_text, steps=branch_steps))

            orelse = getattr(orelse, "orelse", None)

    return IfStep(
        condition=condition,
        steps=steps,
        branches=branches,
        else_steps=else_steps,
    )


def _parse_while_stmt(stmt: While) -> WhileStep:
    """Parse a WHILE loop."""
    condition = (getattr(stmt, "condition", "") or "").strip()
    if not condition:
        condition = _parse_header_condition(getattr(stmt, "header", None))

    limit = None
    until = False

    header = getattr(stmt, "header", None)
    if header and hasattr(header, "tokens"):
        for token in header.tokens:
            if getattr(token, "type", "") != "OPTION":
                continue
            option = _token_value(token).strip()
            if option.startswith("limit="):
                limit = option.partition("=")[2]
            elif option == "until":
                until = True

    steps = _parse_body(stmt.body) if hasattr(stmt, "body") else []

    return WhileStep(
        condition=condition,
        limit=limit,
        until=until,
        steps=steps,
    )


def _parse_try_stmt(stmt: Try) -> TryStep:
    """Parse a TRY/EXCEPT/ELSE/FINALLY block."""
    steps = _parse_body(stmt.body) if hasattr(stmt, "body") else []
    excepts = []
    else_steps = []
    finally_steps = []

    # TRY uses a linked list via 'next' attribute.
    current = getattr(stmt, "next", None)
    while current:
        header = getattr(current, "header", None)
        values = _values(header.tokens) if header and hasattr(header, "tokens") else []
        label = values[0] if values else ""

        if label == "EXCEPT":
            patterns = []
            variable = None
            index = 1
            while index < len(values):
                if values[index] == "AS":
                    variable = values[index + 1] if index + 1 < len(values) else None
                    break
                patterns.append(values[index])
                index += 1
            except_steps = _parse_body(current.body) if hasattr(current, "body") else []
            excepts.append(
                ExceptClause(
                    patterns=patterns,
                    variable=variable,
                    steps=except_steps,
                )
            )
        elif label == "ELSE":
            else_steps = _parse_body(current.body) if hasattr(current, "body") else []
        elif label == "FINALLY":
            finally_steps = (
                _parse_body(current.body) if hasattr(current, "body") else []
            )

        current = getattr(current, "next", None)

    return TryStep(
        steps=steps,
        excepts=excepts,
        else_steps=else_steps,
        finally_steps=finally_steps,
    )


def _parse_var_stmt(stmt: Var) -> VarStep:
    """Parse a VAR statement."""
    name = ""
    value = ""
    scope = None

    for token in getattr(stmt, "tokens", []):
        token_type = getattr(token, "type", "")
        raw = _token_value(token).strip()
        if not raw or raw == "VAR":
            continue
        if token_type == "OPTION" and raw.startswith("scope="):
            scope = raw.partition("=")[2].upper()
        elif token_type == "VARIABLE":
            name = raw
        elif token_type == "ARGUMENT":
            value = raw

    return VarStep(name=name, value=value, scope=scope)


def _parse_return_stmt(stmt: Return) -> ReturnStep:
    """Parse a RETURN statement."""
    values = [
        value for value in _values(getattr(stmt, "tokens", [])) if value != "RETURN"
    ]
    return ReturnStep(values=values)


def _parse_body(body: list[Any]) -> list[Step]:
    """Parse a list of statements into canvas steps."""
    steps: list[Step] = []
    for stmt in body:
        if isinstance(stmt, EmptyLine):
            continue
        if isinstance(stmt, Comment):
            text = " ".join(_values(getattr(stmt, "tokens", [])))
            steps.append(
                CommentStep(text=text if text.startswith("#") else f"# {text}")
            )
            continue
        if isinstance(stmt, (KeywordCall, TemplateArguments)):
            steps.append(_parse_keyword_call(stmt))
        elif isinstance(stmt, If):
            steps.append(_parse_if_stmt(stmt))
        elif isinstance(stmt, For):
            steps.append(_parse_for_stmt(stmt))
        elif isinstance(stmt, While):
            steps.append(_parse_while_stmt(stmt))
        elif isinstance(stmt, Try):
            steps.append(_parse_try_stmt(stmt))
        elif isinstance(stmt, Var):
            steps.append(_parse_var_stmt(stmt))
        elif isinstance(stmt, Return):
            steps.append(_parse_return_stmt(stmt))
        elif isinstance(stmt, Break):
            steps.append(BreakStep())
        elif isinstance(stmt, Continue):
            steps.append(ContinueStep())
        elif isinstance(stmt, Error):
            # Robot parser treats RETURN as an Error statement
            values = _values(getattr(stmt, "tokens", []))
            if values and values[0] == "RETURN":
                steps.append(_parse_return_stmt(stmt))
            else:
                raw_text = " ".join(values)
                if raw_text.strip():
                    steps.append(RawStep(lines=[raw_text]))
        elif isinstance(stmt, Documentation):
            values = _values(getattr(stmt, "tokens", []))
            doc = " ".join(value for value in values if value != "[Documentation]")
            steps.append(CommentStep(text=f"# {doc}"))
        else:
            # Fallback: preserve as raw
            raw_text = " ".join(_values(getattr(stmt, "tokens", [])))
            if raw_text.strip():
                steps.append(RawStep(lines=[raw_text]))
    return steps


def _parse_test_case(test: TestCase) -> CanvasTestCase:
    """Parse a TestCase into canvas model."""
    name = getattr(test, "name", "Unnamed")
    doc = ""
    tags = []
    setup = None
    teardown = None
    timeout = None
    template = None
    steps: list[Step] = []

    for stmt in getattr(test, "body", []):
        if isinstance(stmt, Documentation):
            values = _values(getattr(stmt, "tokens", []))
            doc = " ".join(value for value in values if value != "[Documentation]")
        elif isinstance(stmt, Tags):
            values = _values(getattr(stmt, "tokens", []))
            tags = [value for value in values if value != "[Tags]"]
        elif isinstance(stmt, Setup):
            setup = _parse_setup_teardown(stmt)
        elif isinstance(stmt, Teardown):
            teardown = _parse_setup_teardown(stmt)
        elif isinstance(stmt, Timeout):
            values = _values(getattr(stmt, "tokens", []))
            timeout = next((value for value in values if value != "[Timeout]"), None)
        elif isinstance(stmt, Template):
            values = _values(getattr(stmt, "tokens", []))
            template = next((value for value in values if value != "[Template]"), None)
        elif isinstance(stmt, TemplateArguments):
            # This is a test step using template
            steps.append(_parse_keyword_call(stmt))
        elif isinstance(
            stmt,
            (KeywordCall, If, For, While, Try, Var, Return, Break, Continue, Error),
        ):
            step_list = _parse_body([stmt])
            if step_list:
                steps.extend(step_list)
        elif isinstance(stmt, EmptyLine):
            continue
        elif isinstance(stmt, Comment):
            text = " ".join(_values(getattr(stmt, "tokens", [])))
            steps.append(
                CommentStep(text=text if text.startswith("#") else f"# {text}")
            )
        else:
            raw_text = " ".join(_values(getattr(stmt, "tokens", [])))
            if raw_text.strip():
                steps.append(RawStep(lines=[raw_text]))

    return CanvasTestCase(
        id="",
        name=name,
        documentation=doc,
        tags=tags,
        setup=setup,
        teardown=teardown,
        timeout=timeout,
        template=template,
        steps=steps,
    )


def _parse_keyword(keyword: Keyword) -> KeywordDefinition:
    """Parse a Keyword into canvas model."""
    name = getattr(keyword, "name", "Unnamed")
    args = []
    doc = ""
    tags = []
    teardown = None
    steps: list[Step] = []

    for stmt in getattr(keyword, "body", []):
        if isinstance(stmt, Arguments):
            values = _values(getattr(stmt, "tokens", []))
            args = [value for value in values if value != "[Arguments]"]
        elif isinstance(stmt, Documentation):
            values = _values(getattr(stmt, "tokens", []))
            doc = " ".join(value for value in values if value != "[Documentation]")
        elif isinstance(stmt, Tags):
            values = _values(getattr(stmt, "tokens", []))
            tags = [value for value in values if value != "[Tags]"]
        elif isinstance(stmt, Teardown):
            teardown = _parse_setup_teardown(stmt)
        elif isinstance(
            stmt,
            (KeywordCall, If, For, While, Try, Var, Return, Break, Continue, Error),
        ):
            step_list = _parse_body([stmt])
            if step_list:
                steps.extend(step_list)
        elif isinstance(stmt, EmptyLine):
            continue
        elif isinstance(stmt, Comment):
            text = " ".join(_values(getattr(stmt, "tokens", [])))
            steps.append(
                CommentStep(text=text if text.startswith("#") else f"# {text}")
            )
        else:
            raw_text = " ".join(_values(getattr(stmt, "tokens", [])))
            if raw_text.strip():
                steps.append(RawStep(lines=[raw_text]))

    return KeywordDefinition(
        name=name,
        arguments=args,
        documentation=doc,
        tags=tags,
        teardown=teardown,
        steps=steps,
    )


def import_robot_file(path: Path | str) -> CanvasDocument:
    """Import a .robot file and return a CanvasDocument."""
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    model = get_model(source)

    name = path.stem
    documentation = ""
    libraries = []
    resources = []
    variables = []
    suite_setup = None
    suite_teardown = None
    test_setup = None
    test_teardown = None
    force_tags = []
    default_tags = []
    test_timeout = None
    metadata = {}
    tests = []
    keywords = []

    for section in model.sections:
        section_type = type(section).__name__

        if section_type == "SettingSection":
            for item in section.body:
                if isinstance(item, Documentation):
                    values = _values(getattr(item, "tokens", []))
                    documentation = " ".join(
                        value for value in values if value != "Documentation"
                    )
                elif isinstance(item, LibraryImport):
                    lib_name = getattr(item, "name", "")
                    lib_alias = getattr(item, "alias", None)
                    lib_args = getattr(item, "args", [])
                    libraries.append(
                        CanvasLibraryImport(
                            name=lib_name, alias=lib_alias, args=lib_args
                        )
                    )
                elif isinstance(item, ResourceImport):
                    resources.append(
                        CanvasResourceImport(path=getattr(item, "name", ""))
                    )
                elif isinstance(item, SuiteSetup):
                    suite_setup = _parse_setup_teardown(item)
                elif isinstance(item, SuiteTeardown):
                    suite_teardown = _parse_setup_teardown(item)
                elif isinstance(item, TestSetup):
                    test_setup = _parse_setup_teardown(item)
                elif isinstance(item, TestTeardown):
                    test_teardown = _parse_setup_teardown(item)
                elif isinstance(item, DefaultTags):
                    values = _values(getattr(item, "tokens", []))
                    default_tags = [
                        value
                        for value in values
                        if value not in ("[Default Tags]", "Default Tags")
                    ]
                elif isinstance(item, TestTags):
                    values = _values(getattr(item, "tokens", []))
                    label = values[0] if values else ""
                    if "Force" in label:
                        force_tags = [
                            value
                            for value in values
                            if value not in ("[Force Tags]", "Force Tags")
                        ]
                    else:
                        default_tags = [
                            value
                            for value in values
                            if value not in ("[Default Tags]", "Default Tags")
                        ]
                elif isinstance(item, TestTimeout):
                    values = _values(getattr(item, "tokens", []))
                    test_timeout = (
                        " ".join(value for value in values if value != "Test Timeout")
                        or None
                    )
                elif isinstance(item, Metadata):
                    metadata[getattr(item, "name", "")] = _first_arg_value(
                        getattr(item, "tokens", [])
                    )
                elif isinstance(item, Variable):
                    variables.append(
                        CanvasVariable(
                            name=getattr(item, "name", ""),
                            value=_first_arg_value(getattr(item, "tokens", [])),
                        )
                    )

        elif section_type == "VariableSection":
            for item in section.body:
                if isinstance(item, Variable):
                    variables.append(
                        CanvasVariable(
                            name=getattr(item, "name", ""),
                            value=_first_arg_value(getattr(item, "tokens", [])),
                        )
                    )

        elif section_type == "TestCaseSection":
            for item in section.body:
                if isinstance(item, TestCase):
                    tests.append(_parse_test_case(item))

        elif section_type == "KeywordSection":
            for item in section.body:
                if isinstance(item, Keyword):
                    keywords.append(_parse_keyword(item))

    settings = SuiteSettings(
        documentation=documentation,
        libraries=libraries,
        resources=resources,
        variables=variables,
        suite_setup=suite_setup,
        suite_teardown=suite_teardown,
        test_setup=test_setup,
        test_teardown=test_teardown,
        force_tags=force_tags,
        default_tags=default_tags,
        test_timeout=test_timeout,
        metadata=metadata,
    )

    return CanvasDocument(
        version=1,
        name=name,
        settings=settings,
        tests=tests,
        keywords=keywords,
    )
