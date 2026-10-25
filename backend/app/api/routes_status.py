from fastapi import APIRouter

from app.models.status import GlobalStatus
from app.services.container import get_container
from app.services.status_service import build_global_status

router = APIRouter(tags=["status"])


@router.get("/api/status", response_model=GlobalStatus)
def get_status() -> GlobalStatus:
    return build_global_status(get_container())
