import shutil
import time
from collections.abc import Callable

from app.core.config import Settings
from app.models.tests import TestDefinition, TestListResult, TestResult, TestRunAllResult
from app.services.garmin_auth_service import GarminAuthService
from app.services.mcp_probe_service import probe_mcp_endpoint
from app.services.mcp_service import McpService
from app.services.tunnel_service import TunnelService
from app.utils.ports import is_port_open


class TestService:
    def __init__(
        self,
        settings: Settings,
        garmin: GarminAuthService,
        mcp: McpService,
        tunnel: TunnelService,
    ) -> None:
        self.settings = settings
        self.garmin = garmin
        self.mcp = mcp
        self.tunnel = tunnel

    def list_tests(self) -> TestListResult:
        return TestListResult(tests=[definition for definition, _ in self._checks().values()])

    def run_test(self, test_id: str) -> TestResult:
        checks = self._checks()
        if test_id not in checks:
            return TestResult(
                id=test_id,
                name=test_id,
                state="failed",
                duration_ms=0,
                message="Test inconnu.",
                suggestion="Choisis un test listé par /api/tests.",
            )
        definition, check = checks[test_id]
        started = time.perf_counter()
        try:
            ok, message, suggestion = check()
        except Exception as exc:  # noqa: BLE001 - surfaced as diagnostic result
            ok, message, suggestion = False, f"Erreur pendant le test: {exc}", "Consulte les logs."
        duration_ms = int((time.perf_counter() - started) * 1000)
        return TestResult(
            id=definition.id,
            name=definition.name,
            state="success" if ok else "failed",
            duration_ms=duration_ms,
            message=message,
            suggestion=suggestion if not ok else None,
        )

    def run_all(self) -> TestRunAllResult:
        return TestRunAllResult(results=[self.run_test(test_id) for test_id in self._checks()])

    def _checks(
        self,
    ) -> dict[str, tuple[TestDefinition, Callable[[], tuple[bool, str, str | None]]]]:
        return {
            "check_config": (
                TestDefinition(
                    id="check_config",
                    name="Configuration chargée",
                    description="Valide la configuration centrale.",
                ),
                self._check_config,
            ),
            "check_dependencies": (
                TestDefinition(
                    id="check_dependencies",
                    name="Dépendances disponibles",
                    description="Vérifie uvx et cloudflared.",
                ),
                self._check_dependencies,
            ),
            "check_garmin_token_exists": (
                TestDefinition(
                    id="check_garmin_token_exists",
                    name="Token Garmin détecté",
                    description="Cherche les tokens Garmin locaux.",
                ),
                self._check_token,
            ),
            "check_garmin_auth_valid": (
                TestDefinition(
                    id="check_garmin_auth_valid",
                    name="Auth Garmin valide",
                    description="Lance la vérification Garmin officielle.",
                ),
                self._check_auth,
            ),
            "check_mcp_process": (
                TestDefinition(
                    id="check_mcp_process",
                    name="Process MCP actif",
                    description="Vérifie le processus MCP géré.",
                ),
                self._check_mcp_process,
            ),
            "check_mcp_port": (
                TestDefinition(
                    id="check_mcp_port",
                    name="Port local MCP ouvert",
                    description="Teste le port 127.0.0.1:8080.",
                ),
                self._check_mcp_port,
            ),
            "check_mcp_endpoint": (
                TestDefinition(
                    id="check_mcp_endpoint",
                    name="Endpoint local /mcp",
                    description="Teste l'endpoint MCP local.",
                ),
                self._check_mcp_endpoint,
            ),
            "check_mcp_tools_list": (
                TestDefinition(
                    id="check_mcp_tools_list",
                    name="Liste des outils MCP",
                    description="Classe les outils connus.",
                ),
                self._check_mcp_tools,
            ),
            "check_cloudflared_available": (
                TestDefinition(
                    id="check_cloudflared_available",
                    name="Cloudflared disponible",
                    description="Vérifie la commande cloudflared.",
                ),
                self._check_cloudflared,
            ),
            "check_tunnel_process": (
                TestDefinition(
                    id="check_tunnel_process",
                    name="Tunnel Cloudflare actif",
                    description="Vérifie le processus tunnel.",
                ),
                self._check_tunnel_process,
            ),
            "check_tunnel_public_url": (
                TestDefinition(
                    id="check_tunnel_public_url",
                    name="URL publique détectée",
                    description="Extrait l'URL Cloudflare.",
                ),
                self._check_tunnel_url,
            ),
            "check_remote_mcp_endpoint": (
                TestDefinition(
                    id="check_remote_mcp_endpoint",
                    name="Endpoint distant /mcp",
                    description="Teste l'URL publique.",
                ),
                self._check_remote_endpoint,
            ),
            "check_chatgpt_url_format": (
                TestDefinition(
                    id="check_chatgpt_url_format",
                    name="Format URL ChatGPT",
                    description="Valide l'URL à copier.",
                ),
                self._check_chatgpt_url,
            ),
            "full_smoke_test": (
                TestDefinition(
                    id="full_smoke_test",
                    name="Smoke test complet",
                    description="Vérifie les prérequis critiques.",
                ),
                self._check_smoke,
            ),
        }

    def _check_config(self) -> tuple[bool, str, str | None]:
        return (
            True,
            f"Configuration {self.settings.app.name} {self.settings.app.version} chargée.",
            None,
        )

    def _check_dependencies(self) -> tuple[bool, str, str | None]:
        missing = [
            command
            for command in ("uvx", self.settings.cloudflare.command)
            if shutil.which(command) is None
        ]
        if missing:
            return (
                False,
                f"Dépendances absentes: {', '.join(missing)}.",
                "Installe uv et cloudflared.",
            )
        return True, "Dépendances minimales disponibles.", None

    def _check_token(self) -> tuple[bool, str, str | None]:
        if self.garmin.has_garmin_token():
            return True, "Token Garmin détecté.", None
        return False, "Aucun token Garmin détecté.", "Lance l'authentification assistée."

    def _check_auth(self) -> tuple[bool, str, str | None]:
        status = self.garmin.verify_garmin_auth()
        return (
            status.token_valid,
            status.message,
            "Réauthentifie Garmin." if not status.token_valid else None,
        )

    def _check_mcp_process(self) -> tuple[bool, str, str | None]:
        status = self.mcp.get_mcp_status()
        return status.process.status == "running", status.process.message, "Démarre le service MCP."

    def _check_mcp_port(self) -> tuple[bool, str, str | None]:
        ok = is_port_open(self.settings.mcp.host, self.settings.mcp.port)
        return ok, "Port MCP ouvert." if ok else "Port MCP fermé.", "Démarre MCP ou libère le port."

    def _check_mcp_endpoint(self) -> tuple[bool, str, str | None]:
        health = self.mcp.healthcheck_mcp()
        return health.ok, health.message, "Vérifie le proxy MCP local." if not health.ok else None

    def _check_mcp_tools(self) -> tuple[bool, str, str | None]:
        tools = self.mcp.classify_mcp_tools()
        return True, f"{len(tools.read_tools)} lecture, {len(tools.write_tools)} écriture.", None

    def _check_cloudflared(self) -> tuple[bool, str, str | None]:
        ok = shutil.which(self.settings.cloudflare.command) is not None
        return (
            ok,
            "cloudflared disponible." if ok else "cloudflared introuvable.",
            "Installe cloudflared.",
        )

    def _check_tunnel_process(self) -> tuple[bool, str, str | None]:
        status = self.tunnel.get_tunnel_status()
        return status.state == "running", status.process.message, "Allume le tunnel."

    def _check_tunnel_url(self) -> tuple[bool, str, str | None]:
        url = self.tunnel._get_public_url()
        return (
            bool(url),
            url or "Aucune URL publique.",
            "Attends le démarrage ou consulte les logs Cloudflare.",
        )

    def _check_remote_endpoint(self) -> tuple[bool, str, str | None]:
        url = self.tunnel._get_chatgpt_mcp_url()
        if not url:
            return False, "Aucune URL /mcp publique.", "Allume le tunnel."
        if not url.startswith("https://"):
            return False, "L'URL publique doit être HTTPS.", "Vérifie la configuration du tunnel."
        # Probe MCP réel sur l'URL distante (sans session, juste initialize)
        base_url = url.replace("/mcp", "")
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Thread AnyIO sans boucle – asyncio.run lève la sienne
                timeout = self.settings.timeouts.healthcheck_seconds
                probe = asyncio.run(
                    probe_mcp_endpoint(base_url, timeout_seconds=timeout),
                )
            else:
                if loop.is_running():
                    timeout = self.settings.timeouts.healthcheck_seconds
                    future = asyncio.run_coroutine_threadsafe(
                        probe_mcp_endpoint(base_url, timeout_seconds=timeout),
                        loop,
                    )
                    probe = future.result(timeout=timeout + 5)
                else:
                    timeout = self.settings.timeouts.healthcheck_seconds
                    probe = asyncio.run(
                        probe_mcp_endpoint(base_url, timeout_seconds=timeout),
                    )
        except Exception as exc:
            return False, f"Probe distant échoué: {exc}", "Vérifie tunnel et MCP."
        if probe.ok:
            msg = (
                f"MCP distant OK – {probe.tools_count} outil(s), "
                f"serveur {probe.server_name or 'inconnu'}."
            )
            return True, msg, None
        if probe.error and "530" in str(probe.error):
            return (
                False, probe.error,
                "Démarre le service MCP local puis régénère le tunnel Cloudflare.",
            )
        return (
            False,
            probe.error or "Probe MCP distant a échoué.",
            "Vérifie l'état du tunnel et du service MCP.",
        )

    def _check_chatgpt_url(self) -> tuple[bool, str, str | None]:
        url = self.tunnel._get_chatgpt_mcp_url()
        ok = bool(url and url.startswith("https://") and url.endswith(self.settings.mcp.endpoint))
        return ok, url or "URL absente.", "Le tunnel doit fournir une URL HTTPS terminée par /mcp."

    def _check_smoke(self) -> tuple[bool, str, str | None]:
        config_ok, _, _ = self._check_config()
        dependency_ok, _, _ = self._check_dependencies()
        token_ok, _, _ = self._check_token()
        mcp_ok, _, _ = self._check_mcp_port()
        url_ok, _, _ = self._check_chatgpt_url()
        ok = config_ok and dependency_ok and token_ok and mcp_ok and url_ok
        return (
            ok,
            "Smoke test complet terminé." if ok else "Smoke test incomplet.",
            None if ok else "Corrige les tests échoués au-dessus avant d'utiliser ChatGPT.",
        )
