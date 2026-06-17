"""Tests for Access orchestration (start/stop ChatGPT access).

Cas testés (backend uniquement — sans serveur FastAPI) :
  A. ensure_tunnel — tunnel stopped → start_tunnel est appelé
  B. ensure_tunnel — tunnel running → no-op, URL conservée
  C. ensure_tunnel — tunnel starting → no-op
  D. access stop → MCP arrêté, tunnel inchangé
  E. Routes enregistrées
"""

import sys

from app.core.config import Settings
from app.services.healthcheck_service import HealthcheckService
from app.services.mcp_service import McpService
from app.services.process_manager import ProcessManager
from app.services.state_store import StateStore
from app.services.tunnel_service import TunnelService

from .test_config_security import _settings_dict


def _make_settings(tmp_path) -> Settings:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    s = Settings.model_validate(raw)
    s.ensure_directories()
    return s


def _make_tunnel_service(tmp_path) -> TunnelService:
    settings = _make_settings(tmp_path)
    return TunnelService(settings, ProcessManager(settings), StateStore(settings))


def _make_mcp_service(tmp_path) -> McpService:
    settings = _make_settings(tmp_path)
    return McpService(settings, ProcessManager(settings), HealthcheckService(settings))


def _start_fake_tunnel(svc: TunnelService, tmp_path) -> None:
    """Démarre un faux processus cloudflared et écrit une URL dans le log
    pour que get_tunnel_status() retourne "running" (mode quick)."""
    result = svc.process_manager.start(
        "cloudflared",
        [sys.executable, "-c", "import time; time.sleep(60)"],
    )
    assert result.ok is True

    # Écrire le log avec une URL pour que le statut passe à "running"
    log_dir = svc.settings.logs.path
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "cloudflared.log").write_text(
        "INF https://abc-123.trycloudflare.com ready\n",
        encoding="utf-8",
    )
    # Le cache URL dans _current_url est vide; on force la relecture
    # en appelant _get_public_url() qui va parser le log
    url = svc._get_public_url()
    assert url is not None, "L'URL doit être parsée depuis le log"
    assert svc.get_tunnel_status().state == "running", (
        "Le tunnel doit être 'running' après avoir écrit l'URL"
    )


# ── Cas A : ensure_tunnel avec tunnel stopped → start_tunnel est appelé ──


def test_ensure_tunnel_stopped_starts_tunnel(tmp_path) -> None:
    svc = _make_tunnel_service(tmp_path)
    initial = svc.get_tunnel_status()
    assert initial.state == "stopped"

    result = svc.ensure_tunnel()
    # Le processus a bien été lancé (même si cloudflared n'existe pas,
    # on utilise le chemin de python)
    assert result.ok is True
    assert result.status in ("starting", "error")


# ── Cas B : ensure_tunnel avec tunnel running → no-op ──


def test_ensure_tunnel_running_is_noop(tmp_path) -> None:
    svc = _make_tunnel_service(tmp_path)
    _start_fake_tunnel(svc, tmp_path)
    status = svc.get_tunnel_status()
    assert status.state == "running"
    assert status.chatgpt_mcp_url is not None

    # ensure_tunnel doit retourner un no-op
    noop = svc.ensure_tunnel()
    assert noop.ok is True
    assert noop.status == "running"
    assert "déjà running" in noop.message

    # L'URL ne doit pas avoir été effacée
    assert noop.chatgpt_mcp_url is not None

    # Nettoyage
    svc.process_manager.stop("cloudflared")


# ── Cas C : ensure_tunnel avec tunnel starting → no-op ──


def test_ensure_tunnel_starting_is_noop(tmp_path) -> None:
    svc = _make_tunnel_service(tmp_path)
    # Démarrer le processus sans écrire d'URL → le statut reste "starting"
    result = svc.process_manager.start(
        "cloudflared",
        [sys.executable, "-c", "import time; time.sleep(60)"],
    )
    assert result.ok is True
    status = svc.get_tunnel_status()
    assert status.state == "starting"  # pas d'URL dans le log

    noop = svc.ensure_tunnel()
    assert noop.ok is True
    assert "déjà" in noop.message

    svc.process_manager.stop("cloudflared")


# ── Cas D : stop MCP ne touche pas au tunnel ──


def test_stop_mcp_does_not_stop_tunnel(tmp_path) -> None:
    tunnel_svc = _make_tunnel_service(tmp_path)
    mcp_svc = _make_mcp_service(tmp_path)

    # Démarrer un faux tunnel avec URL
    _start_fake_tunnel(tunnel_svc, tmp_path)
    assert tunnel_svc.get_tunnel_status().state == "running"

    # Démarrer MCP puis l'arrêter (simule stopAccess)
    mr = mcp_svc.start_mcp_service()
    assert mr.ok is True
    mcp_svc.stop_mcp_service()

    # Le tunnel doit encore tourner
    tunnel_after = tunnel_svc.get_tunnel_status()
    assert tunnel_after.state == "running"
    assert tunnel_after.chatgpt_mcp_url is not None

    tunnel_svc.process_manager.stop("cloudflared")


# ── Cas E : vérification des endpoints ──


def test_access_endpoints_are_registered(tmp_path) -> None:
    """Les endpoints sont correctement enregistrés dans le routeur."""
    from app.api.routes_access import router

    routes = [r.path for r in router.routes]
    assert "/api/access/start" in routes
    assert "/api/access/stop" in routes
