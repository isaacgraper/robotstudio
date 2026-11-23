"""Keyword discovery and documentation through Robot Framework libdoc."""

from __future__ import annotations

import os
import re
from functools import lru_cache

from pydantic import BaseModel, Field
from robot.libdoc import LibraryDocumentation

DEFAULT_LIBRARIES: tuple[str, ...] = (
    "BuiltIn",
    "Collections",
    "String",
    "OperatingSystem",
    "Process",
    "DateTime",
    "XML",
)

CURATED: dict[str, str] = {
    "Comment": "Logging",
    "Log": "Logging",
    "Log Many": "Logging",
    "Log To Console": "Logging",
    "Sleep": "Flow",
    "Wait Until Keyword Succeeds": "Flow",
    "Run Keyword And Continue On Failure": "Flow",
    "Run Keyword And Expect Error": "Flow",
    "Run Keyword And Ignore Error": "Flow",
    "Run Keywords": "Flow",
    "Set Variable": "Flow",
    "Set Suite Variable": "Flow",
    "Set Test Variable": "Flow",
    "Evaluate": "Flow",
    "Should Be Empty": "Verify",
    "Should Be Equal": "Verify",
    "Should Be Equal As Integers": "Verify",
    "Should Be Equal As Numbers": "Verify",
    "Should Be Equal As Strings": "Verify",
    "Should Be True": "Verify",
    "Should Contain": "Verify",
    "Should Match": "Verify",
    "Should Not Be Empty": "Verify",
    "Should Not Be Equal": "Verify",
    "Should Not Contain": "Verify",
    "Length Should Be": "Verify",
    "Convert To Integer": "Data",
    "Convert To Number": "Data",
    "Convert To String": "Data",
    "Create Dictionary": "Data",
    "Create List": "Data",
    "Get From Dictionary": "Data",
    "Get From List": "Data",
    "Get Length": "Data",
    "Set To Dictionary": "Data",
    "Append To List": "Data",
    "Create File": "Files",
    "Directory Should Exist": "Files",
    "File Should Exist": "Files",
    "Get File": "Files",
    "Remove File": "Files",
    "Run Process": "Process",
    "Get Current Date": "Time",
    "Add Time To Date": "Time",
    "Convert Time": "Time",
    "Subtract Time From Date": "Time",
}

_EMBEDDED = re.compile(r"\$\{([^}]+)\}")


class ArgumentInfo(BaseModel):
    """A keyword argument as described by libdoc."""

    name: str
    kind: str
    required: bool = True
    default: str | None = None
    type: str = "object"
    typedoc: str | None = None
    documentation: str = ""
    representation: str = ""


class KeywordInfo(BaseModel):
    """A callable keyword with enough detail to render an editor."""

    name: str
    library: str
    documentation: str = ""
    short_documentation: str = ""
    arguments: list[ArgumentInfo] = Field(default_factory=list)
    embedded_arguments: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    curated: bool = False
    deprecated: bool = False
    source: str | None = None
    line: int | None = None


class LibraryInfo(BaseModel):
    """A library that was inspected successfully."""

    name: str
    version: str | None = None
    documentation: str = ""
    keyword_count: int = 0


class LibraryFailure(BaseModel):
    """A library that could not be inspected."""

    name: str
    error: str


class Catalog(BaseModel):
    """The keyword catalog returned to the editor."""

    libraries: list[LibraryInfo] = Field(default_factory=list)
    failures: list[LibraryFailure] = Field(default_factory=list)
    keywords: list[KeywordInfo] = Field(default_factory=list)

    @property
    def curated_keywords(self) -> list[KeywordInfo]:
        """Return only the hand-picked operator-facing keywords."""
        return [keyword for keyword in self.keywords if keyword.curated]


def configured_libraries() -> list[str]:
    """Return the default libraries plus any configured extras."""
    libraries = list(DEFAULT_LIBRARIES)
    extra = os.environ.get("ROBOT_CANVAS_LIBRARIES", "")
    for name in extra.split(","):
        cleaned = name.strip()
        if cleaned and cleaned not in libraries:
            libraries.append(cleaned)
    return libraries


@lru_cache(maxsize=4)
def _build_catalog(libraries: tuple[str, ...]) -> Catalog:
    catalog = Catalog()
    for library_name in libraries:
        try:
            documentation = LibraryDocumentation(library_name)
        except Exception as error:  # noqa: BLE001 - report any import failure
            error_msg = f"{type(error).__name__}: {error}"
            catalog.failures.append(LibraryFailure(name=library_name, error=error_msg))
            continue
        catalog.libraries.append(
            LibraryInfo(
                name=documentation.name,
                version=documentation.version,
                documentation=documentation.doc,
                keyword_count=len(documentation.keywords),
            )
        )
        for keyword in documentation.keywords:
            if keyword.private or keyword.name.startswith("_"):
                continue
            catalog.keywords.append(_keyword_info(documentation.name, keyword))
    catalog.keywords.sort(key=lambda item: (item.library, item.name.lower()))
    return catalog


def _keyword_info(library: str, keyword: object) -> KeywordInfo:
    name = getattr(keyword, "name", "")
    dictionary: dict[str, object] = getattr(keyword, "to_dictionary", lambda: {})()
    arguments = [
        ArgumentInfo(
            name=argument["name"],
            kind=argument["kind"],
            required=argument["required"],
            default=argument.get("defaultValue"),
            type=(argument.get("type") or {}).get("name", "object"),
            typedoc=(argument.get("type") or {}).get("typedoc"),
            documentation=argument.get("doc", ""),
            representation=argument.get("repr", ""),
        )
        for argument in dictionary.get("args", [])  # type: ignore[attr-defined]
    ]
    category = CURATED.get(name, library)
    return KeywordInfo(
        name=name,
        library=library,
        documentation=str(dictionary.get("doc", "")),
        short_documentation=str(dictionary.get("shortdoc", "")),
        arguments=arguments,
        embedded_arguments=_EMBEDDED.findall(name),
        tags=list(dictionary.get("tags", [])),  # type: ignore[attr-defined,call-overload,arg-type]
        category=category,
        curated=name in CURATED,
        deprecated=bool(getattr(keyword, "deprecated", False)),
        source=str(dictionary.get("source")),  # type: ignore[attr-defined,arg-type]
        line=int(dictionary.get("lineno", 0)),  # type: ignore[attr-defined,call-overload,arg-type]
    )


def load_catalog(libraries: list[str] | None = None) -> Catalog:
    """Inspect libraries and return their keywords."""
    names = tuple(libraries) if libraries else tuple(configured_libraries())
    return _build_catalog(names)


def clear_catalog_cache() -> None:
    """Drop the cached catalog, for example after installing a library."""
    _build_catalog.cache_clear()
