"""JUnit XML export, understood by SonarQube, GitLab, Jenkins and friends."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from robotstudio.model.results import CaseResult, RunSummary


def build_junit(summary: RunSummary) -> str:
    """Render a run summary as a JUnit XML document."""
    root = ET.Element(
        "testsuites",
        {
            "name": "robotstudio",
            "tests": str(summary.total),
            "failures": str(summary.failed),
            "errors": str(0),
            "skipped": str(summary.skipped),
            "time": _seconds(summary.duration_ms),
        },
    )
    suite = ET.SubElement(
        root,
        "testsuite",
        {
            "name": summary.stem,
            "tests": str(summary.total),
            "failures": str(summary.failed),
            "errors": str(0),
            "skipped": str(summary.skipped),
            "timestamp": summary.started_at,
            "time": _seconds(summary.duration_ms),
        },
    )
    for case in summary.cases:
        _append_case(suite, summary.stem, case)
    if summary.error:
        ET.SubElement(
            suite,
            "system-err",
        ).text = summary.error
    ET.indent(ET.ElementTree(root), space="  ")
    payload: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    return payload.decode("utf-8")


def _append_case(parent: ET.Element, stem: str, case: CaseResult) -> None:
    element = ET.SubElement(
        parent,
        "testcase",
        {
            "classname": f"{stem}.{case.suite}",
            "name": case.name,
            "time": _seconds(case.elapsed_ms),
        },
    )
    status = case.status.upper()
    if status == "FAIL":
        failure = ET.SubElement(
            element,
            "failure",
            {"message": _first_line(case.message), "type": "AssertionError"},
        )
        failure.text = case.message
    elif status == "SKIP":
        ET.SubElement(element, "skipped", {"message": case.message})


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def _first_line(message: str) -> str:
    return message.strip().splitlines()[0] if message.strip() else ""
