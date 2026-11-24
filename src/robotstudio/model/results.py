"""Models describing the outcome of a Robot Framework run."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RunStatus = Literal["passed", "failed", "timeout", "error"]


class CaseResult(BaseModel):
    """Result of a single test case."""

    name: str
    suite: str
    status: str
    message: str = ""
    elapsed_ms: int = 0
    tags: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Aggregate result of running one suite."""

    run_id: str
    stem: str
    status: RunStatus
    started_at: str
    finished_at: str
    duration_ms: int
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    cases: list[CaseResult] = Field(default_factory=list)
    output_dir: str
    error: str | None = None
