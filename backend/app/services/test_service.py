import shutil
import time
from collections.abc import Callable

from app.core.config import Settings
from app.models.tests import TestDefinition, TestListResult, TestResult, TestRunAllResult
from app.services.garmin_auth_service import GarminAuthService
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
                    description="Vérifie les dépendances Python.",
                ),
                self._check_dependencies,
            ),
            "check_garmin_api_key": (
                TestDefinition(
                    id="check_garmin_api_key",
                    name="Clé API Garmin détectée",
                    description=(
                        "Cherche une clé Personal API dans l'environnement "
                        "ou le fichier officiel."
                    ),
                ),
                self._check_api_key,
            ),
            "check_garmin_auth_valid": (
                TestDefinition(
                    id="check_garmin_auth_valid",
                    name="Connexion Garmin valide",
                    description="Échange la clé API et lit le profil Garmin.",
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
            "check_tunnel_client_installed": (
                TestDefinition(
                    id="check_tunnel_client_installed",
                    name="Client tunnel OpenAI installé",
                    description="Vérifie le binaire tunnel-client.",
                ),
                self._check_tunnel_client,
            ),
            "check_tunnel_process": (
                TestDefinition(
                    id="check_tunnel_process",
                    name="Tunnel OpenAI actif",
                    description="Vérifie le processus tunnel-client.",
                ),
                self._check_tunnel_process,
            ),
            "check_tunnel_ready": (
                TestDefinition(
                    id="check_tunnel_ready",
                    name="Tunnel OpenAI prêt",
                    description="Vérifie /readyz du tunnel-client.",
                ),
                self._check_tunnel_ready,
            ),
            "check_tunnel_configured": (
                TestDefinition(
                    id="check_tunnel_configured",
                    name="Tunnel OpenAI configuré",
                    description="Vérifie le tunnel ID et la clé API ChatGPT.",
                ),
                self._check_tunnel_connector,
            ),
            "check_chatgpt_connector": (
                TestDefinition(
                    id="check_chatgpt_connector",
                    name="Connecteur ChatGPT",
                    description="Vérifie que ChatGPT peut utiliser le tunnel.",
                ),
                self._check_chatgpt_connector,
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
        if shutil.which("uvx") is None:
            return False, "uvx introuvable.", "Installe uv."
        return True, "Dépendances Python disponibles.", None

    def _check_tunnel_client(self) -> tuple[bool, str, str | None]:
        binary = self.tunnel.binary.status()
        if binary.installed:
            return (
                True,
                f"tunnel-client installé ({binary.version or 'version inconnue'}).",
                None,
            )
        return (
            False,
            "tunnel-client non installé.",
            "Ouvre /tunnel pour l'installer automatiquement.",
        )

    def _check_api_key(self) -> tuple[bool, str, str | None]:
        status = self.garmin.status()
        if not status.configured:
            return (
                False,
                "Aucune clé API Garmin détectée.",
                "Ouvre /connexion et colle ta clé Personal API.",
            )
        source = "variable d'environnement" if status.key.source == "env" else "fichier officiel"
        return True, f"Clé API Garmin détectée ({source}).", None

    def _check_auth(self) -> tuple[bool, str, str | None]:
        status = self.garmin.verify()
        ok = status.state in {"valid", "expiring_soon"}
        return (
            ok,
            status.message,
            "Vérifie la clé dans /connexion." if not ok else None,
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
        result = self.mcp.list_mcp_tools()
        if not result.ok:
            return (
                False,
                result.message,
                "Vérifie que le proxy MCP local est démarré.",
            )
        tools = result.tools
        reads = sum(1 for tool in tools if tool.risk == "read")
        writes = sum(1 for tool in tools if tool.risk == "write")
        return True, f"{reads} lecture, {writes} écriture.", None

    def _check_tunnel_process(self) -> tuple[bool, str, str | None]:
        status = self.tunnel.get_tunnel_status()
        return status.state == "running", status.process.message, "Allume le tunnel."

    def _check_tunnel_ready(self) -> tuple[bool, str, str | None]:
        status = self.tunnel.get_tunnel_status()
        return (
            status.ready,
            status.last_event or "Tunnel non prêt.",
            "Démarre le tunnel OpenAI et consulte /tunnel.",
        )

    def _check_tunnel_connector(self) -> tuple[bool, str, str | None]:
        config = self.tunnel.get_config_status()
        if not config.configured:
            return (
                False,
                "Tunnel OpenAI non configuré.",
                "Ouvre /tunnel pour renseigner le tunnel ID et la clé API ChatGPT.",
            )
        return True, f"Tunnel configuré: {config.tunnel_id}.", None

    def _check_chatgpt_connector(self) -> tuple[bool, str, str | None]:
        status = self.tunnel.get_tunnel_status()
        ok = status.ready and bool(status.tunnel_id)
        return (
            ok,
            (
                f"Tunnel prêt: {status.tunnel_id}. "
                "ChatGPT → Connectors → Connection: Tunnel."
                if ok
                else status.last_event or "Tunnel non prêt."
            ),
            "Démarre le tunnel et vérifie /readyz dans /tunnel.",
        )

    def _check_smoke(self) -> tuple[bool, str, str | None]:
        config_ok, _, _ = self._check_config()
        dependency_ok, _, _ = self._check_dependencies()
        token_ok, _, _ = self._check_api_key()
        tunnel_client_ok, _, _ = self._check_tunnel_client()
        mcp_ok, _, _ = self._check_mcp_port()
        tunnel_ok, _, _ = self._check_chatgpt_connector()
        ok = (
            config_ok
            and dependency_ok
            and token_ok
            and tunnel_client_ok
            and mcp_ok
            and tunnel_ok
        )
        return (
            ok,
            "Smoke test complet terminé." if ok else "Smoke test incomplet.",
            None if ok else "Corrige les tests échoués au-dessus avant d'utiliser ChatGPT.",
        )
