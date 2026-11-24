"""End-to-end tests for running and exporting suites."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from robotstudio.model.canvas import (
    Argument,
    CallStep,
    CanvasDocument,
    KeywordRef,
    TestCase,
)
from robotstudio.runner import RunError, export_run, list_runs, load_run, run_suite
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import Workspace


@pytest.fixture()
def workspace(tmp_path: Path) -> Workspace:
    store = Workspace(tmp_path)
    store.save(demo_document(), "demo")
    return store


def test_run_demo_suite_passes(workspace: Workspace) -> None:
    summary = run_suite(workspace, "demo")
    assert summary.status == "passed"
    assert summary.total == 3
    assert summary.passed == 3
    assert summary.failed == 0
    assert all(case.status == "PASS" for case in summary.cases)
    assert Path(summary.output_dir).is_dir()
    assert (Path(summary.output_dir) / "summary.json").is_file()
    assert (Path(summary.output_dir) / "robot" / "output.xml").is_file()


def test_failed_suite_reports_failure(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    document = CanvasDocument(
        name="Broken",
        tests=[
            TestCase(
                name="Expects Equality",
                steps=[
                    CallStep(
                        keyword=KeywordRef(name="Should Be Equal"),
                        args=[Argument(value="1"), Argument(value="2")],
                    )
                ],
            )
        ],
    )
    workspace.save(document, "broken")

    summary = run_suite(workspace, "broken")
    assert summary.status == "failed"
    assert summary.failed == 1
    assert "1" in summary.cases[0].message and "2" in summary.cases[0].message


def test_run_records_are_listed_and_loaded(workspace: Workspace) -> None:
    first = run_suite(workspace, "demo")
    second = run_suite(workspace, "demo")
    summaries = list_runs(workspace)
    assert {item.run_id for item in summaries} == {first.run_id, second.run_id}
    assert load_run(workspace, first.run_id).run_id == first.run_id


def test_export_junit_and_bundle(workspace: Workspace) -> None:
    summary = run_suite(workspace, "demo")
    junit_path, junit_type = export_run(workspace, summary.run_id, "junit")
    assert junit_type == "application/xml"
    assert "<testsuites" in junit_path.read_text(encoding="utf-8")

    bundle_path, bundle_type = export_run(workspace, summary.run_id, "bundle")
    assert bundle_type == "application/zip"
    with zipfile.ZipFile(bundle_path) as archive:
        assert "manifest.json" in archive.namelist()


def test_unknown_run_and_format_raise(workspace: Workspace) -> None:
    with pytest.raises(RunError):
        load_run(workspace, "missing")
    with pytest.raises(RunError):
        export_run(workspace, "missing", "junit")
    summary = run_suite(workspace, "demo")
    with pytest.raises(RunError):
        export_run(workspace, summary.run_id, "pdf")


def test_missing_suite_raises_run_error(workspace: Workspace) -> None:
    with pytest.raises(RunError):
        run_suite(workspace, "absent")
