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
    LibraryImport,
    Metadata,
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
    Timeout,
    Variable,
)

from robot_canvas.model.canvas import (
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
from robot_canvas.model.canvas import (
    LibraryImport as CanvasLibraryImport,
)
from robot_canvas.model.canvas import (
    TestCase as CanvasTestCase,
)
from robot_canvas.model.canvas import (
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


def _parse_header_condition(header: Any) -> str:
    """Extract condition text from a control structure header."""
    if not header or not hasattr(header, "tokens"):
        return ""
    parts = []
    skip_next = False
    for token in header.tokens:
        if skip_next:
            skip_next = False
            continue
        val = _token_value(token)
        if val in ("IF", "ELSE", "FOR", "WHILE", "TRY", "EXCEPT", "FINALLY"):
            skip_next = True  # Skip the following separator
            continue
        if val.strip() and val != "\n":
            parts.append(val)
    return " ".join(parts)


def _parse_keyword_call(stmt: Any) -> CallStep:
    """Parse a KeywordCall or TemplateArguments into a CallStep."""
    tokens = getattr(stmt, "tokens", [])
    values = _token_values(tokens)

    # Check for assignment like ${var} =
    keyword_name = None
    args = []
    assign = []

    i = 0
    while i < len(values):
        v = values[i].strip()
        if not v:
            i += 1
            continue
        if v.endswith("=") and v.startswith("${"):
            # Assignment target
            assign.append(v.rstrip(" ="))
        elif keyword_name is None:
            keyword_name = v
        elif "=" in v and not v.startswith("${"):
            # Named argument
            parts = v.split("=", 1)
            args.append(Argument(name=parts[0], value=parts[1]))
        else:
            args.append(Argument(value=v))
        i += 1

    if keyword_name is None:
        keyword_name = "Unknown"

    # Check for embedded arguments in keyword name
    embedded = {}
    import re

    for match in re.finditer(r"\$\{([^}]+)\}", keyword_name):
        embedded[match.group(1)] = ""

    return CallStep(
        keyword=KeywordRef(name=keyword_name, embedded=embedded),
        args=args,
        assign=assign,
    )


def _parse_setup_teardown(stmt: Any) -> CallStep | None:
    """Parse a Setup/Teardown statement."""
    header = getattr(stmt, "header", None)
    if header and hasattr(header, "tokens"):
        values = _token_values(header.tokens)
        # Header format: [Setup/Teardown] Keyword arg1 arg2...
        kw_values = [
            v
            for v in values
            if v.strip() not in ("[Setup]", "[Teardown]", "Setup", "Teardown")
        ]
        if kw_values:
            keyword_name = kw_values[0]
            args = [Argument(value=v) for v in kw_values[1:]]
            return CallStep(keyword=KeywordRef(name=keyword_name), args=args)
    # Fallback to tokens
    tokens = getattr(stmt, "tokens", [])
    values = _token_values(tokens)
    if len(values) < 2:
        return None
    keyword_name = values[1] if len(values) > 1 else "Unknown"
    args = [Argument(value=v) for v in values[2:]]
    return CallStep(keyword=KeywordRef(name=keyword_name), args=args)


def _parse_for_stmt(stmt: For) -> ForStep:
    """Parse a FOR loop."""
    header = getattr(stmt, "header", None)
    variables: list[str] = []
    flavor: Literal["in", "in_range", "in_enumerate", "in_zip"] = "in"
    loop_values: list[str] = []

    if header and hasattr(header, "tokens"):
        tokens = header.tokens
        values = _token_values(tokens)
        in_seen = False
        for v in values:
            v_stripped = v.strip()
            if v_stripped in ("FOR", "END"):
                continue
            if v_stripped in ("IN", "IN_RANGE", "IN_ENUMERATE", "IN_ZIP"):
                if v_stripped in ("IN_RANGE", "IN_ENUMERATE", "IN_ZIP"):
                    flavor = v_stripped  # type: ignore[assignment]
                in_seen = True
                continue
            if v_stripped and not in_seen:
                variables.append(v_stripped)
            elif v_stripped and in_seen:
                loop_values.append(v_stripped)

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
    condition = getattr(stmt, "condition", "") or ""
    if not condition:
        condition = _parse_header_condition(getattr(stmt, "header", None))

    limit = None
    until = False

    # Check for LIMIT and UNTIL in header
    header = getattr(stmt, "header", None)
    if header and hasattr(header, "tokens"):
        values = _token_values(header.tokens)
        for i, v in enumerate(values):
            v_stripped = v.strip()
            if v_stripped == "LIMIT" and i + 1 < len(values):
                limit = values[i + 1]
            if v_stripped == "UNTIL":
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

    # TRY uses a linked list via 'next' attribute
    current = getattr(stmt, "next", None)
    while current:
        header_text = ""
        if hasattr(current, "header") and current.header:
            header_tokens = current.header.tokens
            header_text = " ".join(_token_value(t) for t in header_tokens).strip()

        if "EXCEPT" in header_text.upper():
            patterns = getattr(current, "patterns", ()) or ()
            variable = (
                getattr(current, "variable", None)
                or getattr(current, "assign", None)
                or "error"
            )
            if isinstance(variable, (list, tuple)):
                variable = variable[0] if variable else "error"
            except_steps = _parse_body(current.body) if hasattr(current, "body") else []
            excepts.append(
                ExceptClause(
                    patterns=list(patterns),
                    variable=variable,
                    steps=except_steps,
                )
            )

        elif "ELSE" in header_text.upper():
            else_steps = _parse_body(current.body) if hasattr(current, "body") else []

        elif "FINALLY" in header_text.upper():
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
    tokens = getattr(stmt, "tokens", [])
    values = _token_values(tokens)
    name = ""
    value = ""
    scope = None

    for v in values:
        v_stripped = v.strip()
        if v_stripped in ("VAR", "SCOPE"):
            continue
        if v_stripped.upper() in ("TEST", "TASK", "SUITE", "GLOBAL"):
            scope = v_stripped.upper()
        elif not name:
            name = v_stripped
        else:
            value = v_stripped

    return VarStep(name=name, value=value, scope=scope)


def _parse_return_stmt(stmt: Return) -> ReturnStep:
    """Parse a RETURN statement."""
    tokens = getattr(stmt, "tokens", [])
    values = _token_values(tokens)
    return_values = [v for v in values if v.strip() not in ("RETURN",)]
    return ReturnStep(values=return_values)


def _parse_body(body: list[Any]) -> list[Step]:
    """Parse a list of statements into canvas steps."""
    steps: list[Step] = []
    for stmt in body:
        if isinstance(stmt, EmptyLine):
            continue
        if isinstance(stmt, Comment):
            text = " ".join(_token_values(getattr(stmt, "tokens", [])))
            steps.append(CommentStep(text=f"# {text}"))
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
        elif isinstance(stmt, Documentation):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            doc = " ".join(v for v in values if v not in ("[Documentation]",))
            steps.append(CommentStep(text=f"# {doc}"))
        else:
            # Fallback: preserve as raw
            tokens = getattr(stmt, "tokens", [])
            raw_text = " ".join(_token_values(tokens))
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
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            doc = " ".join(v for v in values if v not in ("[Documentation]",))
        elif isinstance(stmt, Tags):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            tags = [v.strip() for v in values if v.strip() and v not in ("[Tags]",)]
        elif isinstance(stmt, Setup):
            setup = _parse_setup_teardown(stmt)
        elif isinstance(stmt, Teardown):
            teardown = _parse_setup_teardown(stmt)
        elif isinstance(stmt, Timeout):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            timeout = next((v for v in values if v not in ("[Timeout]",)), None)
        elif isinstance(stmt, Template):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            template = next((v for v in values if v not in ("[Template]",)), None)
        elif isinstance(stmt, TemplateArguments):
            # This is a test step using template
            steps.append(_parse_keyword_call(stmt))
        elif isinstance(
            stmt, (KeywordCall, If, For, While, Try, Var, Return, Break, Continue)
        ):
            step_list = _parse_body([stmt])
            if step_list:
                steps.extend(step_list)
        elif isinstance(stmt, EmptyLine):
            continue
        elif isinstance(stmt, Comment):
            text = " ".join(_token_values(getattr(stmt, "tokens", [])))
            steps.append(CommentStep(text=f"# {text}"))
        else:
            tokens = getattr(stmt, "tokens", [])
            raw_text = " ".join(_token_values(tokens))
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
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            args = [
                v.strip() for v in values if v.strip() and v not in ("[Arguments]",)
            ]
        elif isinstance(stmt, Documentation):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            doc = " ".join(v for v in values if v not in ("[Documentation]",))
        elif isinstance(stmt, Tags):
            tokens = getattr(stmt, "tokens", [])
            values = _token_values(tokens)
            tags = [v.strip() for v in values if v.strip() and v not in ("[Tags]",)]
        elif isinstance(stmt, Teardown):
            teardown = _parse_setup_teardown(stmt)
        elif isinstance(
            stmt, (KeywordCall, If, For, While, Try, Var, Return, Break, Continue)
        ):
            step_list = _parse_body([stmt])
            if step_list:
                steps.extend(step_list)
        elif isinstance(stmt, EmptyLine):
            continue
        elif isinstance(stmt, Comment):
            text = " ".join(_token_values(getattr(stmt, "tokens", [])))
            steps.append(CommentStep(text=f"# {text}"))
        else:
            tokens = getattr(stmt, "tokens", [])
            raw_text = " ".join(_token_values(tokens))
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
    _set_source_lines(source)
    model = get_model(source)

    name = path.stem
    libraries = []
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
                if isinstance(item, LibraryImport):
                    lib_name = getattr(item, "name", "")
                    lib_alias = getattr(item, "alias", None)
                    lib_args = getattr(item, "args", [])
                    libraries.append(
                        CanvasLibraryImport(
                            name=lib_name, alias=lib_alias, args=lib_args
                        )
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
                    tokens = getattr(item, "tokens", [])
                    values = _token_values(tokens)
                    default_tags = [
                        v.strip()
                        for v in values
                        if v.strip() and v not in ("[Default Tags]", "Default Tags")
                    ]
                elif isinstance(item, TestTags):
                    tokens = getattr(item, "tokens", [])
                    values = _token_values(tokens)
                    # Check if it's Force Tags or Default Tags
                    first_token = values[0] if values else ""
                    if "Force" in first_token:
                        force_tags = [
                            v.strip()
                            for v in values
                            if v.strip() and v not in ("[Force Tags]", "Force Tags")
                        ]
                    else:
                        default_tags = [
                            v.strip()
                            for v in values
                            if v.strip() and v not in ("[Default Tags]", "Default Tags")
                        ]
                elif isinstance(item, Metadata):
                    tokens = getattr(item, "tokens", [])
                    values = _token_values(tokens)
                    if len(values) >= 2:
                        metadata[values[0]] = values[1]
                elif isinstance(item, Variable):
                    # Extract variable name from source using line/column info
                    var_name = _extract_var_name_from_source(
                        item.lineno,
                        item.col_offset,
                        item.end_lineno,
                        item.end_col_offset,
                    )
                    tokens = getattr(item, "tokens", [])
                    var_value = _first_arg_value(tokens)
                    if var_name:
                        variables.append(CanvasVariable(name=var_name, value=var_value))
                    else:
                        # Fallback: try to get name from tokens
                        tokens = getattr(item, "tokens", [])
                        values = _token_values(tokens)
                        if len(values) >= 2:
                            variables.append(
                                CanvasVariable(name=values[0].strip(), value=var_value)
                            )

        elif section_type == "VariableSection":
            for item in section.body:
                if isinstance(item, Variable):
                    var_name = _extract_var_name_from_source(
                        item.lineno,
                        item.col_offset,
                        item.end_lineno,
                        item.end_col_offset,
                    )
                    tokens = getattr(item, "tokens", [])
                    var_value = _first_arg_value(tokens)
                    if var_name:
                        variables.append(CanvasVariable(name=var_name, value=var_value))
                    else:
                        tokens = getattr(item, "tokens", [])
                        values = _token_values(tokens)
                        if len(values) >= 2:
                            variables.append(
                                CanvasVariable(name=values[0].strip(), value=var_value)
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
        documentation="",
        libraries=libraries,
        resources=[],
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
