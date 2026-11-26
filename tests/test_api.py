"""HTTP API tests for the FastAPI layer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from robotstudio.api.app import create_app
from robotstudio.workspace.demo import demo_document


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path))


def test_health(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["version"]


def test_init_then_list_and_get(client: TestClient) -> None:
    created = client.post("/api/init").json()
    assert created["created"] is True
    assert created["suite"]["stem"] == "robotstudio-demo"

    suites = client.get("/api/suites").json()
    assert [entry["stem"] for entry in suites] == ["robotstudio-demo"]

    detail = client.get("/api/suites/robotstudio-demo").json()
    assert detail["document"]["name"] == "Robotstudio Demo"


def test_create_suite(client: TestClient) -> None:
    response = client.post("/api/suites/new", json={"name": "My Suite"})
    assert response.status_code == 200
    created = response.json()
    assert created["stem"] == "my-suite"
    assert created["document"]["name"] == "My Suite"
    assert created["document"]["tests"] == []

    suites = client.get("/api/suites").json()
    assert [entry["stem"] for entry in suites] == ["my-suite"]


def test_create_suite_requires_a_name(client: TestClient) -> None:
    assert client.post("/api/suites/new", json={"name": "   "}).status_code == 400


def test_create_suite_rejects_a_duplicate(client: TestClient) -> None:
    assert client.post("/api/suites/new", json={"name": "Dup"}).status_code == 200
    assert client.post("/api/suites/new", json={"name": "Dup"}).status_code == 409


def test_preview_and_validate(client: TestClient) -> None:
    document = demo_document().model_dump(mode="json")
    preview = client.post("/api/preview", json={"document": document}).json()
    assert preview["validation"]["ok"] is True
    assert preview["robot_text"].startswith("*** Settings ***")

    validated = client.post(
        "/api/validate", json={"document": document, "dry_run": True}
    ).json()
    assert validated["validation"]["test_count"] == 3


def test_run_list_and_export(client: TestClient) -> None:
    client.post("/api/init")
    summary = client.post(
        "/api/suites/robotstudio-demo/run", json={"timeout": 120}
    ).json()
    assert summary["status"] == "passed"
    assert summary["passed"] == 3

    runs = client.get("/api/runs").json()
    assert runs[0]["run_id"] == summary["run_id"]

    detail = client.get(f"/api/runs/{summary['run_id']}").json()
    assert detail["stem"] == "robotstudio-demo"

    export = client.get(f"/api/runs/{summary['run_id']}/export/junit")
    assert export.status_code == 200
    assert "<testsuites" in export.text


def test_run_missing_suite_returns_400(client: TestClient) -> None:
    response = client.post("/api/suites/absent/run")
    assert response.status_code == 400


def test_unknown_export_returns_404(client: TestClient) -> None:
    assert client.get("/api/runs/missing/export/junit").status_code == 404


def test_delete_suite(client: TestClient) -> None:
    client.post("/api/init")
    assert client.delete("/api/suites/robotstudio-demo").json() == {"deleted": True}
    assert client.get("/api/suites").json() == []


def test_run_disabled_returns_403(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path, allow_run=False))
    client.post("/api/init")
    resp = client.post("/api/suites/robotstudio-demo/run")
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()

    # health still reports allow_run
    health = client.get("/api/health").json()
    assert health["allow_run"] is False


def test_run_enabled_by_default(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    client.post("/api/init")
    resp = client.post("/api/suites/robotstudio-demo/run")
    assert resp.status_code == 200

    health = client.get("/api/health").json()
    assert health["allow_run"] is True
