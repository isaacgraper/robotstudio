"""Pydantic models for the Robotstudio document."""

from __future__ import annotations

import hashlib
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

StepType = Literal[
    "call",
    "if",
    "for",
    "while",
    "try",
    "var",
    "return",
    "break",
    "continue",
    "comment",
    "raw",
]


class Argument(BaseModel):
    """One keyword argument, optionally named."""

    name: str | None = None
    value: str = ""


class KeywordRef(BaseModel):
    """Reference to a keyword, including embedded argument values."""

    name: str
    source: str | None = None
    embedded: dict[str, str] = Field(default_factory=dict)


class CallStep(BaseModel):
    """A keyword call."""

    type: Literal["call"] = "call"
    keyword: KeywordRef
    args: list[Argument] = Field(default_factory=list)
    assign: list[str] = Field(default_factory=list)
    comment: str | None = None


class IfStep(BaseModel):
    """An IF / ELSE IF / ELSE block."""

    type: Literal["if"] = "if"
    condition: str
    steps: list[Step] = Field(default_factory=list)
    branches: list[IfStep] = Field(default_factory=list)
    else_steps: list[Step] = Field(default_factory=list)


class ForStep(BaseModel):
    """A FOR loop."""

    type: Literal["for"] = "for"
    variables: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    flavor: Literal["in", "in_range", "in_enumerate", "in_zip"] = "in"
    steps: list[Step] = Field(default_factory=list)


class WhileStep(BaseModel):
    """A WHILE loop."""

    type: Literal["while"] = "while"
    condition: str
    limit: str | None = None
    until: bool = False
    steps: list[Step] = Field(default_factory=list)


class ExceptClause(BaseModel):
    """One EXCEPT branch."""

    patterns: list[str] = Field(default_factory=list)
    variable: str | None = None
    steps: list[Step] = Field(default_factory=list)


class TryStep(BaseModel):
    """A TRY / EXCEPT / ELSE / FINALLY block."""

    type: Literal["try"] = "try"
    steps: list[Step] = Field(default_factory=list)
    excepts: list[ExceptClause] = Field(default_factory=list)
    else_steps: list[Step] = Field(default_factory=list)
    finally_steps: list[Step] = Field(default_factory=list)


class VarStep(BaseModel):
    """A VAR statement."""

    type: Literal["var"] = "var"
    name: str
    value: str = ""
    scope: str | None = None


class ReturnStep(BaseModel):
    """A RETURN statement."""

    type: Literal["return"] = "return"
    values: list[str] = Field(default_factory=list)


class BreakStep(BaseModel):
    """A BREAK statement."""

    type: Literal["break"] = "break"


class ContinueStep(BaseModel):
    """A CONTINUE statement."""

    type: Literal["continue"] = "continue"


class CommentStep(BaseModel):
    """A comment line."""

    type: Literal["comment"] = "comment"
    text: str = ""


class RawStep(BaseModel):
    """Raw Robot lines preserved from an imported suite."""

    type: Literal["raw"] = "raw"
    lines: list[str] = Field(default_factory=list)


Step = Annotated[
    CallStep
    | IfStep
    | ForStep
    | WhileStep
    | TryStep
    | VarStep
    | ReturnStep
    | BreakStep
    | ContinueStep
    | CommentStep
    | RawStep,
    Field(discriminator="type"),
]


class LibraryImport(BaseModel):
    """A library import in ``*** Settings ***``."""

    name: str
    alias: str | None = None
    args: list[str] = Field(default_factory=list)


class ResourceImport(BaseModel):
    """A resource import in ``*** Settings ***``."""

    path: str


class Variable(BaseModel):
    """A suite variable."""

    name: str
    value: str = ""


class SuiteSettings(BaseModel):
    """Everything in ``*** Settings ***`` and ``*** Variables ***``."""

    documentation: str = ""
    libraries: list[LibraryImport] = Field(default_factory=list)
    resources: list[ResourceImport] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    suite_setup: CallStep | None = None
    suite_teardown: CallStep | None = None
    test_setup: CallStep | None = None
    test_teardown: CallStep | None = None
    force_tags: list[str] = Field(default_factory=list)
    default_tags: list[str] = Field(default_factory=list)
    test_timeout: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TestCase(BaseModel):
    """A test case in ``*** Test Cases ***``."""

    id: str = ""
    name: str
    documentation: str = ""
    tags: list[str] = Field(default_factory=list)
    setup: CallStep | None = None
    teardown: CallStep | None = None
    timeout: str | None = None
    template: str | None = None
    steps: list[Step] = Field(default_factory=list)

    @model_validator(mode="after")
    def assign_id(self) -> TestCase:
        """Give every test a stable identifier when one is missing."""
        if not self.id:
            digest = hashlib.sha1(self.name.encode("utf-8")).hexdigest()[:10]
            self.id = f"tc_{digest}"
        return self


class KeywordDefinition(BaseModel):
    """A user keyword in ``*** Keywords ***``."""

    name: str
    arguments: list[str] = Field(default_factory=list)
    documentation: str = ""
    tags: list[str] = Field(default_factory=list)
    teardown: CallStep | None = None
    steps: list[Step] = Field(default_factory=list)


class CanvasDocument(BaseModel):
    """The complete, versioned canvas document."""

    version: int = 1
    name: str
    settings: SuiteSettings = Field(default_factory=SuiteSettings)
    tests: list[TestCase] = Field(default_factory=list)
    keywords: list[KeywordDefinition] = Field(default_factory=list)

    def robot_text(self) -> str:
        """Render this document as Robot Framework source."""
        from robotstudio.generator.writer import write_document

        return write_document(self)

    def summary(self) -> dict[str, Any]:
        """Return a small JSON-friendly description."""
        return {
            "name": self.name,
            "tests": len(self.tests),
            "keywords": len(self.keywords),
            "libraries": [library.name for library in self.settings.libraries],
        }


if_step = IfStep.model_rebuild()
for_step = ForStep.model_rebuild()
while_step = WhileStep.model_rebuild()
try_step = TryStep.model_rebuild()
except_clause = ExceptClause.model_rebuild()
test_case = TestCase.model_rebuild()
keyword_definition = KeywordDefinition.model_rebuild()
suite_settings = SuiteSettings.model_rebuild()
canvas_document = CanvasDocument.model_rebuild()
