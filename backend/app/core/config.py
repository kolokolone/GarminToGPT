import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.paths import project_root, resolve_project_path


class AppConfig(BaseModel):
    name: str = "GarminToGPT"
    version: str = "1.0.0"
    environment: str = "local"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_port: int = 3000

    @field_validator("host")
    @classmethod
    def require_localhost(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("server.host must stay bound to 127.0.0.1")
        return value


class McpConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    endpoint: str = "/mcp"
    sse_endpoint: str = "/sse"
    command: list[str]
    proxy_command: list[str] = Field(default_factory=list)

    @field_validator("host")
    @classmethod
    def require_localhost(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("mcp.host must stay bound to 127.0.0.1")
        return value


class GarminConfig(BaseModel):
    """Official Garmin Connect Personal API settings.

    Key and token cache paths deliberately follow Garmin's own client
    (``~/.config/garmin/...``) so the backend and the MCP server share them.
    Tests can override them with ``GARMINTOGPT_GARMIN_KEY_FILE`` and
    ``GARMINTOGPT_GARMIN_TOKEN_CACHE``.
    """

    rotation_warning_days: int = 7
    timeout_seconds: int = 30

    @field_validator("rotation_warning_days")
    @classmethod
    def validate_warning_days(cls, value: int) -> int:
        if not 1 <= value <= 90:
            raise ValueError("garmin.rotation_warning_days must be between 1 and 90")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        if not 5 <= value <= 120:
            raise ValueError("garmin.timeout_seconds must be between 5 and 120")
        return value


class CloudflareConfig(BaseModel):
    mode: Literal["quick", "named"] = "quick"
    local_url: str = "http://127.0.0.1:8080"
    tunnel_name: str = ""
    hostname: str = ""
    command: str = "cloudflared"


class RuntimeConfig(BaseModel):
    dir: str = "runtime"
    pid_dir: str = "runtime/pids"
    state_file: str = "runtime/state.json"

    @property
    def runtime_path(self) -> Path:
        return resolve_project_path(self.dir)

    @property
    def pid_path(self) -> Path:
        return resolve_project_path(self.pid_dir)

    @property
    def state_path(self) -> Path:
        return resolve_project_path(self.state_file)


class LogsConfig(BaseModel):
    dir: str = "logs"
    max_size_mb: int = 10
    retain_files: int = 5

    @property
    def path(self) -> Path:
        return resolve_project_path(self.dir)


class SecurityConfig(BaseModel):
    bind_local_only: bool = True
    redact_sensitive_logs: bool = True
    allow_write_tools: bool = False


class TimeoutConfig(BaseModel):
    process_start_seconds: int = 45
    process_stop_seconds: int = 15
    healthcheck_seconds: int = 10


class Settings(BaseModel):
    app: AppConfig
    server: ServerConfig
    mcp: McpConfig
    garmin: GarminConfig
    cloudflare: CloudflareConfig
    runtime: RuntimeConfig
    logs: LogsConfig
    security: SecurityConfig
    timeouts: TimeoutConfig

    def ensure_directories(self) -> None:
        for directory in (self.runtime.runtime_path, self.runtime.pid_path, self.logs.path):
            directory.mkdir(parents=True, exist_ok=True)


def config_path() -> Path:
    raw = os.environ.get("GARMINTOGPT_CONFIG", "config/app.yaml")
    path = Path(os.path.expandvars(raw)).expanduser()
    if not path.is_absolute():
        path = project_root() / path
    return path


@lru_cache
def get_settings() -> Settings:
    path = config_path()
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    settings = Settings.model_validate(data)
    settings.ensure_directories()
    return settings
