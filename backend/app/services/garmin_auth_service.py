import shutil
from pathlib import Path

from app.core.config import Settings
from app.models.auth import DisconnectResult, GarminAuthResult, GarminAuthStatus
from app.services.state_store import StateStore
from app.utils.command import run_command
from app.utils.time import utc_now_iso


class GarminAuthService:
    def __init__(self, settings: Settings, state: StateStore) -> None:
        self.settings = settings
        self.state = state

    def has_garmin_token(self) -> bool:
        token_dir = self.settings.garmin.token_path
        return token_dir.exists() and any(path.is_file() for path in token_dir.rglob("*"))

    def get_last_successful_auth_date(self) -> str | None:
        value = self.state.read().get("last_successful_auth")
        return str(value) if value else None

    def verify_garmin_auth(self) -> GarminAuthStatus:
        if not self.has_garmin_token():
            return GarminAuthStatus(
                state="no_token",
                token_found=False,
                token_valid=False,
                message="Aucun token Garmin détecté. Lance l'authentification assistée.",
            )

        result = run_command(
            self.settings.garmin.verify_command,
            timeout_seconds=self.settings.timeouts.healthcheck_seconds,
        )
        if result.ok:
            now = utc_now_iso()
            self.state.set_value("last_successful_auth", now)
            return GarminAuthStatus(
                state="connected",
                token_found=True,
                token_valid=True,
                last_successful_auth=now,
                message="Token Garmin valide.",
            )
        return GarminAuthStatus(
            state="auth_invalid",
            token_found=True,
            token_valid=False,
            last_successful_auth=self.get_last_successful_auth_date(),
            message=result.output or "Le token Garmin existe mais n'est plus valide.",
        )

    def start_garmin_auth(
        self,
        email: str | None = None,
        password: str | None = None,
        otp: str | None = None,
    ) -> GarminAuthResult:
        _ = (email, password, otp)
        status = self.verify_garmin_auth() if self.has_garmin_token() else self._status_no_token()
        return GarminAuthResult(
            ok=False,
            assisted=True,
            message=(
                "L'authentification Garmin MCP est traitée comme un flux assisté: exécute la "
                "commande indiquée dans un terminal local, puis clique sur Vérifier. Aucun mot "
                "de passe n'est stocké par GarminToGPT."
            ),
            command=self.settings.garmin.auth_command,
            status=status,
        )

    def reauthenticate(self) -> GarminAuthResult:
        return self.start_garmin_auth()

    def disconnect_garmin(self, confirm: bool) -> DisconnectResult:
        if not confirm:
            return DisconnectResult(
                ok=False,
                message="Confirmation explicite requise pour supprimer les tokens Garmin.",
            )
        token_dir = self.settings.garmin.token_path
        if not token_dir.exists():
            return DisconnectResult(ok=True, message="Aucun token Garmin à supprimer.")
        for child in token_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
        return DisconnectResult(ok=True, message="Tokens Garmin locaux supprimés.")

    def _status_no_token(self) -> GarminAuthStatus:
        token_dir_name = Path(self.settings.garmin.token_path).name
        return GarminAuthStatus(
            state="no_token",
            token_found=False,
            token_valid=False,
            message=f"Aucun token Garmin détecté dans {token_dir_name}.",
        )
