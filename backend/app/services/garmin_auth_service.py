import os
import shutil
import subprocess
import threading
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
        # --- Assisted flow (no credentials) — backward compat ---
        if not email or not password:
            status = (
                self.verify_garmin_auth()
                if self.has_garmin_token()
                else self._status_no_token()
            )
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

        # --- Interactive flow via subprocess ---
        if otp:
            return self._complete_auth_with_otp(email, password, otp)
        return self._initiate_auth_flow(email, password)

    def _initiate_auth_flow(self, email: str, password: str) -> GarminAuthResult:
        """Premier appel: envoie email/password, détecte si MFA est requis."""
        env = self._auth_env(email, password)
        process = subprocess.Popen(
            self.settings.garmin.auth_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        collected_stdout: list[str] = []
        collected_stderr: list[str] = []
        mfa_detected = threading.Event()

        def _reader(stream, dest, stop_on_mfa: bool = False) -> None:
            for line in iter(stream.readline, ""):
                line_str = line.rstrip("\n\r")
                dest.append(line_str)
                if stop_on_mfa and "Enter MFA code" in line_str:
                    mfa_detected.set()
                    break

        t_out = threading.Thread(
            target=_reader, args=(process.stdout, collected_stdout, True), daemon=True
        )
        t_err = threading.Thread(
            target=_reader, args=(process.stderr, collected_stderr, False), daemon=True
        )
        t_out.start()
        t_err.start()

        # Attendre max 20 s pour le prompt MFA ou la fin du processus
        mfa_detected.wait(timeout=20)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        t_out.join(timeout=3)
        t_err.join(timeout=3)

        output = "\n".join(collected_stdout + collected_stderr)
        status = self.verify_garmin_auth() if self.has_garmin_token() else self._status_no_token()

        if mfa_detected.is_set():
            return GarminAuthResult(
                ok=False,
                needs_otp=True,
                message=(
                    "Un code de vérification a été envoyé à ton email/phone Garmin."
                    " Saisis-le ci-dessous."
                ),
                status=status,
            )

        if process.returncode == 0 and status.token_valid:
            return GarminAuthResult(
                ok=True,
                message="Authentification Garmin réussie.",
                status=status,
            )

        return GarminAuthResult(
            ok=False,
            message=self._clean_auth_message(output),
            status=status,
        )

    def _complete_auth_with_otp(self, email: str, password: str, otp: str) -> GarminAuthResult:
        """Second appel: email/password + OTP pour finaliser l'auth."""
        env = self._auth_env(email, password)
        process = subprocess.Popen(
            self.settings.garmin.auth_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        collected_stdout: list[str] = []
        collected_stderr: list[str] = []

        def _reader(stream, dest) -> None:
            for line in iter(stream.readline, ""):
                dest.append(line.rstrip("\n\r"))

        t_out = threading.Thread(
            target=_reader, args=(process.stdout, collected_stdout), daemon=True
        )
        t_err = threading.Thread(
            target=_reader, args=(process.stderr, collected_stderr), daemon=True
        )
        t_out.start()
        t_err.start()

        try:
            # Laisser le temps au processus de démarrer et d'arriver au prompt MFA
            import time
            time.sleep(2)
            process.stdin.write(otp + "\n")
            process.stdin.flush()
            process.stdin.close()
        except OSError:
            pass

        try:
            process.wait(timeout=self.settings.timeouts.process_start_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        t_out.join(timeout=3)
        t_err.join(timeout=3)

        status = self.verify_garmin_auth() if self.has_garmin_token() else self._status_no_token()

        if process.returncode == 0 and status.token_valid:
            return GarminAuthResult(
                ok=True,
                message="Authentification Garmin réussie.",
                status=status,
            )

        output = "\n".join(collected_stdout + collected_stderr)
        return GarminAuthResult(
            ok=False,
            needs_otp=True,
            message=self._clean_auth_message(output),
            status=status,
        )

    @staticmethod
    def _clean_auth_message(output: str) -> str:
        """Nettoie le message d'erreur pour l'utilisateur."""
        output = output.replace("✗", "").replace("✓", "").strip()
        lines = [ln for ln in output.split("\n") if ln.strip()]
        # Prendre les lignes pertinentes (ignorer les titres/bannières)
        keywords = ("error", "fail", "rate", "invalid", "incorrect", "expired", "MFA")
        relevant = [ln for ln in lines if any(k in ln.lower() for k in keywords)]
        if relevant:
            return relevant[-1].strip()
        if lines:
            return lines[-1].strip()
        return "Erreur d'authentification. Vérifie tes identifiants et réessaie."

    @staticmethod
    def _auth_env(email: str, password: str) -> dict[str, str]:
        env = os.environ.copy()
        env["GARMIN_EMAIL"] = email
        env["GARMIN_PASSWORD"] = password
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        return env

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
