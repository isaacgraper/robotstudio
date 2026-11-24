"""Tests for workspace storage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from robotstudio.model.canvas import CanvasDocument, TestCase
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import Workspace, WorkspaceError, slugify


def test_slugify() -> None:
    assert slugify("Robotstudio Demo") == "robotstudio-demo"
    assert slugify("  Weird __ Name!! ") == "weird-name"
    assert slugify("***") == "suite"


def test_save_writes_both_files(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    saved = workspace.save(demo_document())
    assert saved.stem == "robotstudio-demo"
    assert saved.canvas_path.is_file()
    assert saved.robot_path.is_file()
    assert saved.robot_text == saved.robot_path.read_text(encoding="utf-8")
    payload = json.loads(saved.canvas_path.read_text(encoding="utf-8"))
    assert payload["name"] == "Robotstudio Demo"
    assert payload["tests"][0]["id"].startswith("tc_")


def test_load_round_trips_document(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.save(demo_document(), "round-trip")
    loaded = workspace.load("round-trip")
    assert loaded.name == "Robotstudio Demo"
    assert [test.name for test in loaded.tests][0] == "Log A Greeting"
    assert workspace.robot_text("round-trip").startswith("*** Settings ***")


def test_list_suites_is_newest_first(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.save(CanvasDocument(name="First"), "first")
    workspace.save(CanvasDocument(name="Second"), "second")
    entries = workspace.list_suites()
    assert {entry.stem for entry in entries} == {"first", "second"}
    assert entries[0].updated >= entries[-1].updated


def test_delete_removes_both_files(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    saved = workspace.save(demo_document())
    workspace.delete(saved.stem)
    assert not saved.canvas_path.exists()
    assert not saved.robot_path.exists()
    assert workspace.list_suites() == []


@pytest.mark.parametrize("stem", ["../escape", "Bad Name", "a/b", "", ".hidden"])
def test_invalid_stems_are_rejected(tmp_path: Path, stem: str) -> None:
    workspace = Workspace(tmp_path)
    with pytest.raises(WorkspaceError):
        workspace.save(CanvasDocument(name="Unsafe"), stem)


def test_missing_suite_raises(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    with pytest.raises(WorkspaceError):
        workspace.load("absent")


def test_list_skips_broken_documents(tmp_path: Path) -> None:
    (tmp_path / "broken.canvas.json").write_text("{not json", encoding="utf-8")
    workspace = Workspace(tmp_path)
    workspace.save(CanvasDocument(name="Good"), "good")
    assert [entry.stem for entry in workspace.list_suites()] == ["good"]


def test_stable_ids_survive_rename(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    document = CanvasDocument(name="Suite", tests=[TestCase(name="Original")])
    identifier = document.tests[0].id
    workspace.save(document, "stable")
    document.tests[0].name = "Renamed"
    workspace.save(document, "stable")
    assert workspace.load("stable").tests[0].id == identifier


def test_no_temporary_files_remain(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.save(demo_document())
    assert not list(tmp_path.glob(".robotstudio-*"))
