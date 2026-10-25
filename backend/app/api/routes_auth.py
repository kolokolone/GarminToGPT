from fastapi import APIRouter, HTTPException

from app.garmin_auth import (
    ConfigureKeyRequest,
    GarminAuthError,
    GarminAuthResult,
    GarminAuthStatus,
    RemoveKeyRequest,
    UpdateKeyExpirationRequest,
)
from app.services.container import get_container

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status", response_model=GarminAuthStatus)
def get_auth_status() -> GarminAuthStatus:
    """Return the key/token status without making a network request."""
    return get_container().garmin.status()


@router.post("/key", response_model=GarminAuthResult)
def configure_key(payload: ConfigureKeyRequest) -> GarminAuthResult:
    """Create or replace the Garmin Personal API key (idempotent)."""
    container = get_container()
    try:
        outcome = container.garmin.configure(payload.api_key, payload.expires_on)
    except GarminAuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc

    if outcome.changed:
        _restart_mcp_if_running(container)
    message = (
        "Clé API Garmin mise à jour et vérifiée."
        if outcome.changed
        else "Clé API Garmin déjà enregistrée et vérifiée."
    )
    return GarminAuthResult(
        ok=True,
        changed=outcome.changed,
        message=message,
        status=outcome.status,
    )


@router.patch("/key", response_model=GarminAuthStatus)
def update_key_expiration(payload: UpdateKeyExpirationRequest) -> GarminAuthStatus:
    """Declare or clear the key's expiration date for the rotation countdown."""
    container = get_container()
    try:
        return container.garmin.update_expiration(payload.expires_on)
    except GarminAuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc


@router.delete("/key", response_model=GarminAuthResult)
def remove_key(payload: RemoveKeyRequest) -> GarminAuthResult:
    """Remove the local key and stop the bridge that depended on it."""
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation requise pour supprimer la clé API Garmin.",
        )
    container = get_container()
    try:
        status = container.garmin.remove()
    except GarminAuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc

    container.mcp.stop_mcp_service()
    container.tunnel.stop_tunnel()
    return GarminAuthResult(
        ok=True,
        message="Clé API Garmin supprimée. Le pont a été arrêté.",
        status=status,
    )


@router.post("/verify", response_model=GarminAuthStatus)
def verify_key() -> GarminAuthStatus:
    """Force a fresh token exchange and a small Garmin data read."""
    return get_container().garmin.verify()


def _restart_mcp_if_running(container) -> None:
    if container.mcp.get_local_status().status in {"running", "starting"}:
        container.mcp.restart_mcp_service()
