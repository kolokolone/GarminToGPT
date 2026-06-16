from functools import lru_cache

from app.core.config import get_settings
from app.services.garmin_auth_service import GarminAuthService
from app.services.healthcheck_service import HealthcheckService
from app.services.log_service import LogService
from app.services.mcp_service import McpService
from app.services.process_manager import ProcessManager
from app.services.state_store import StateStore
from app.services.test_service import TestService
from app.services.tunnel_service import TunnelService


class ServiceContainer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.state = StateStore(self.settings)
        self.process_manager = ProcessManager(self.settings)
        self.healthchecks = HealthcheckService(self.settings)
        self.garmin = GarminAuthService(self.settings, self.state)
        self.mcp = McpService(self.settings, self.process_manager, self.healthchecks)
        self.tunnel = TunnelService(self.settings, self.process_manager, self.state)
        self.logs = LogService(self.settings)
        self.tests = TestService(self.settings, self.garmin, self.mcp, self.tunnel)


@lru_cache
def get_container() -> ServiceContainer:
    return ServiceContainer()
