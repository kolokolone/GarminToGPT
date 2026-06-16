from fastapi import APIRouter

from app.models.tests import TestListResult, TestResult, TestRunAllResult
from app.services.container import get_container

router = APIRouter(prefix="/api/tests", tags=["tests"])


@router.get("", response_model=TestListResult)
def list_tests() -> TestListResult:
    return get_container().tests.list_tests()


@router.post("/{test_id}/run", response_model=TestResult)
def run_test(test_id: str) -> TestResult:
    return get_container().tests.run_test(test_id)


@router.post("/run-all", response_model=TestRunAllResult)
def run_all() -> TestRunAllResult:
    return get_container().tests.run_all()
