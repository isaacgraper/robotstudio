"""Tests for the MCP tool layer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from robotstudio.mcp.server import create_server  # noqa: E402
from robotstudio.workspace.demo import demo_document  # noqa: E402
from robotstudio.workspace.store import Workspace  # noqa: E402


@pytest.fixture()
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    Workspace(tmp_path).save(demo_document(), "demo")
    monkeypatch.setenv("ROBOTSTUDIO_WORKSPACE", str(tmp_path))
    return create_server()


def _call(server, name: str, arguments: dict | None = None):
    result = asyncio.run(server.call_tool(name, arguments or {}))
    return json.loads(result[0][0].text)


def test_tools_are_registered(server) -> None:
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "studio_list_suites",
        "studio_get_suite",
        "studio_save_suite",
        "studio_preview",
        "studio_validate",
        "studio_search_keywords",
        "studio_describe_keyword",
        "studio_run_suite",
        "studio_export_run",
    } <= names


def test_list_and_get_suite(server) -> None:
    listing = _call(server, "studio_list_suites")
    assert listing["count"] == 1
    assert listing["suites"][0]["stem"] == "demo"

    detail = _call(server, "studio_get_suite", {"stem": "demo"})
    assert detail["document"]["name"] == "Robotstudio Demo"
    assert detail["robot_text"].startswith("*** Settings ***")


def test_preview_and_validate(server) -> None:
    document = demo_document().model_dump(mode="json")
    preview = _call(server, "studio_preview", {"document": document})
    assert preview["validation"]["ok"] is True
    assert preview["validation"]["test_count"] == 3

    validated = _call(
        server,
        "studio_validate",
        {"document": document, "dry_run_check": True},
    )
    assert validated["ok"] is True


def test_catalog_search_and_describe(server) -> None:
    found = _call(
        server,
        "studio_search_keywords",
        {"query": "should be equal", "limit": 3},
    )
    assert found["count"] >= 1
    assert any(keyword["name"] == "Should Be Equal" for keyword in found["keywords"])

    described = _call(server, "studio_describe_keyword", {"name": "Should Be Equal"})
    assert described["library"] == "BuiltIn"
    assert described["arguments"]


def test_save_then_run_and_export(server, tmp_path: Path) -> None:
    document = demo_document().model_dump(mode="json")
    document["name"] = "MCP Suite"
    saved = _call(server, "studio_save_suite", {"document": document, "stem": "mcp"})
    assert saved["stem"] == "mcp"
    assert saved["validation"]["ok"] is True

    summary = _call(server, "studio_run_suite", {"stem": "mcp"})
    assert summary["status"] == "passed"
    assert summary["passed"] == 3

    exported = _call(
        server, "studio_export_run", {"run_id": summary["run_id"], "format": "junit"}
    )
    assert exported["media_type"] == "application/xml"
    assert Path(exported["path"]).is_file()


def test_unknown_suite_raises(server) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        _call(server, "studio_get_suite", {"stem": "absent"})


def test_no_run_disables_execution_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    Workspace(tmp_path).save(demo_document(), "demo")
    monkeypatch.setenv("ROBOTSTUDIO_WORKSPACE", str(tmp_path))
    server = create_server(allow_run=False)
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert "studio_run_suite" not in names
    # but export and history remain
    assert "studio_list_runs" in names
    assert "studio_export_run" in names


def test_no_run_env_var_disables_execution_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    Workspace(tmp_path).save(demo_document(), "demo")
    monkeypatch.setenv("ROBOTSTUDIO_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("ROBOTSTUDIO_ALLOW_RUN", "false")
    server = create_server()
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert "studio_run_suite" not in names
