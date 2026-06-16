from app.core.config import Settings
from app.models.common import HealthcheckResult
from app.models.mcp import McpStatus, McpTool, McpToolClassification, McpToolsResult
from app.services.healthcheck_service import HealthcheckService
from app.services.process_manager import ProcessManager

WRITE_PREFIXES = ("add_", "set_", "delete_", "remove_", "upload_", "schedule_", "unschedule_")
KNOWN_GARMIN_TOOLS = [
    "get_activities",
    "get_activity",
    "get_stats",
    "get_sleep_summary",
    "add_weigh_in",
    "delete_weigh_ins",
    "upload_workout",
    "schedule_workout",
    "set_activity_name",
]


class McpService:
    def __init__(
        self,
        settings: Settings,
        process_manager: ProcessManager,
        healthchecks: HealthcheckService,
    ) -> None:
        self.settings = settings
        self.process_manager = process_manager
        self.healthchecks = healthchecks

    @property
    def local_url(self) -> str:
        return (
            f"http://{self.settings.mcp.host}:{self.settings.mcp.port}{self.settings.mcp.endpoint}"
        )

    def start_mcp_service(self):
        command = self.settings.mcp.proxy_command or self.settings.mcp.command
        return self.process_manager.start("mcp", command, port=self.settings.mcp.port)

    def stop_mcp_service(self):
        return self.process_manager.stop("mcp")

    def restart_mcp_service(self):
        self.stop_mcp_service()
        return self.start_mcp_service()

    def get_mcp_status(self) -> McpStatus:
        process = self.process_manager.status("mcp")
        healthcheck: HealthcheckResult | None = None
        state = process.status
        if process.status == "running":
            healthcheck = self.healthcheck_mcp()
            state = "running" if healthcheck.ok else "unhealthy"
        return McpStatus(
            state=state,
            host=self.settings.mcp.host,
            port=self.settings.mcp.port,
            endpoint=self.settings.mcp.endpoint,
            local_url=self.local_url,
            process=process,
            healthcheck=healthcheck,
        )

    def healthcheck_mcp(self) -> HealthcheckResult:
        return self.healthchecks.check_http_endpoint(self.local_url)

    def list_mcp_tools(self) -> McpToolsResult:
        tools = [self._classify_tool(name) for name in KNOWN_GARMIN_TOOLS]
        return McpToolsResult(
            ok=False,
            message=(
                "Liste conservatrice basée sur les noms connus garmin-mcp. "
                "L'introspection MCP live sera disponible quand le proxy expose la liste d'outils."
            ),
            tools=tools,
        )

    def classify_mcp_tools(self) -> McpToolClassification:
        tools = self.list_mcp_tools().tools
        return McpToolClassification(
            read_tools=[tool.name for tool in tools if tool.risk == "read"],
            write_tools=[tool.name for tool in tools if tool.risk == "write"],
            unknown_tools=[tool.name for tool in tools if tool.risk == "unknown"],
        )

    def _classify_tool(self, name: str) -> McpTool:
        if name.startswith(WRITE_PREFIXES):
            return McpTool(name=name, risk="write", reason="Préfixe d'action modifiante détecté.")
        if name.startswith("get_") or name.startswith("count_"):
            return McpTool(name=name, risk="read", reason="Préfixe de lecture détecté.")
        return McpTool(name=name, risk="unknown", reason="Risque non déterminé automatiquement.")
