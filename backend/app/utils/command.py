import subprocess
from dataclasses import dataclass
from os import environ

from app.utils.redact import redact_text


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int | None
    output: str


def run_command(command: list[str], timeout_seconds: int) -> CommandResult:
    child_env = environ.copy()
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    child_env.setdefault("PYTHONUTF8", "1")
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return CommandResult(False, None, f"Commande introuvable: {redact_text(str(exc))}")
    except subprocess.TimeoutExpired:
        return CommandResult(False, None, "Commande interrompue: délai dépassé.")

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return CommandResult(
        completed.returncode == 0,
        completed.returncode,
        redact_text(normalize_command_output(output.strip())),
    )


def normalize_command_output(output: str) -> str:
    return output.replace("✓", "OK").replace("✗", "ERREUR")
