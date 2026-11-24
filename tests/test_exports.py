"""Tests for the JUnit, CSV, JSON and bundle exporters."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from robotstudio.exports.bundle import build_bundle, redact_text
from robotstudio.exports.junit import build_junit
from robotstudio.exports.tabular import results_csv, results_json
from robotstudio.model.results import CaseResult, RunSummary
from robotstudio.workspace.demo import demo_document
from robotstudio.workspace.store import Workspace


def _summary(output_dir: Path) -> RunSummary:
    return RunSummary(
        run_id="20260101-000000-abcdef12",
        stem="demo",
        status="failed",
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        duration_ms=1000,
        total=2,
        passed=1,
        failed=1,
        skipped=0,
        cases=[
            CaseResult(
                name="Works",
                suite="Demo",
                status="PASS",
                elapsed_ms=100,
                tags=["smoke"],
            ),
            CaseResult(
                name="Breaks",
                suite="Demo",
                status="FAIL",
                message="Expected 1 but got 2",
                elapsed_ms=900,
            ),
        ],
        output_dir=str(output_dir),
    )


def test_junit_has_one_testcase_per_result(tmp_path: Path) -> None:
    root = ET.fromstring(build_junit(_summary(tmp_path)))
    assert root.tag == "testsuites"
    suite = root.find("testsuite")
    assert suite is not None
    cases = suite.findall("testcase")
    assert [case.get("name") for case in cases] == ["Works", "Breaks"]
    assert cases[1].find("failure") is not None
    assert suite.get("failures") == "1"


def test_results_csv_and_json(tmp_path: Path) -> None:
    summary = _summary(tmp_path)
    csv_text = results_csv(summary)
    assert csv_text.splitlines()[0].startswith("run_id,suite,test,status")
    assert "Breaks,FAIL" in csv_text
    payload = json.loads(results_json(summary))
    assert payload["run_id"] == summary.run_id
    assert payload["cases"][1]["message"] == "Expected 1 but got 2"


def test_redaction_covers_common_secrets() -> None:
    text = (
        "api_key: super-secret\n"
        "password= hunter2\n"
        "url=https://user:pass@example.test/x\n"
        "contact someone@example.test\n"
    )
    cleaned = redact_text(text)
    assert "super-secret" not in cleaned
    assert "hunter2" not in cleaned
    assert "user:pass@" not in cleaned
    assert "someone@example.test" not in cleaned


def test_bundle_contains_results_sources_and_robot_output(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.save(demo_document(), "demo")
    run_dir = tmp_path / ".runs" / "run-1"
    (run_dir / "robot").mkdir(parents=True)
    (run_dir / "robot" / "output.xml").write_text("<robot />", encoding="utf-8")
    summary = _summary(run_dir)
    target = tmp_path / "bundle.zip"

    build_bundle(summary, workspace.root, target)

    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        assert {
            "manifest.json",
            "results/junit.xml",
            "results/results.csv",
            "results/results.json",
            "sources/suite.robot",
            "sources/suite.canvas.json",
            "robot/output.xml",
        } <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["redacted"] is True
