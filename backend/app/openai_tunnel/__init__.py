"""OpenAI Secure MCP Tunnel integration.

The tunnel client is a customer-run daemon that polls the OpenAI control plane
and forwards MCP requests to the local ``mcp-proxy``. It does not expose a
public URL: ChatGPT connects through ``Connection: Tunnel`` and the tunnel ID.

This package owns the tunnel-specific pieces (configuration, binary management,
validation) so ``TunnelService`` stays orchestration-only.
"""

from app.openai_tunnel.binary import (
    RELEASES,
    TunnelBinary,
    TunnelBinaryError,
    TunnelBinaryManager,
)
from app.openai_tunnel.config_store import (
    OpenAITunnelConfigStore,
    StoredTunnelConfig,
    TunnelConfigError,
    TunnelConfigFormatError,
    TunnelEnvConflictError,
    TunnelValidationError,
)
from app.openai_tunnel.validator import TunnelClientValidator, TunnelValidation

__all__ = [
    "OpenAITunnelConfigStore",
    "RELEASES",
    "StoredTunnelConfig",
    "TunnelBinary",
    "TunnelBinaryError",
    "TunnelBinaryManager",
    "TunnelClientValidator",
    "TunnelConfigError",
    "TunnelConfigFormatError",
    "TunnelEnvConflictError",
    "TunnelValidation",
    "TunnelValidationError",
]
