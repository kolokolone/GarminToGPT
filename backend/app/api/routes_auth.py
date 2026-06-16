from fastapi import APIRouter

from app.models.auth import (
    DisconnectRequest,
    DisconnectResult,
    GarminAuthResult,
    GarminAuthStatus,
    GarminLoginRequest,
)
from app.services.container import get_container

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status", response_model=GarminAuthStatus)
def get_auth_status() -> GarminAuthStatus:
    return get_container().garmin.verify_garmin_auth()


@router.post("/login", response_model=GarminAuthResult)
def login(payload: GarminLoginRequest) -> GarminAuthResult:
    return get_container().garmin.start_garmin_auth(payload.email, payload.password, payload.otp)


@router.post("/verify", response_model=GarminAuthStatus)
def verify() -> GarminAuthStatus:
    return get_container().garmin.verify_garmin_auth()


@router.post("/reauthenticate", response_model=GarminAuthResult)
def reauthenticate() -> GarminAuthResult:
    return get_container().garmin.reauthenticate()


@router.post("/disconnect", response_model=DisconnectResult)
def disconnect(payload: DisconnectRequest) -> DisconnectResult:
    return get_container().garmin.disconnect_garmin(payload.confirm)
