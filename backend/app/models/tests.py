from typing import Literal

from pydantic import BaseModel

TestState = Literal["not_run", "running", "success", "failed", "skipped"]


class TestDefinition(BaseModel):
    id: str
    name: str
    description: str


class TestResult(BaseModel):
    id: str
    name: str
    state: TestState
    duration_ms: int
    message: str
    suggestion: str | None = None


class TestListResult(BaseModel):
    tests: list[TestDefinition]


class TestRunAllResult(BaseModel):
    results: list[TestResult]
