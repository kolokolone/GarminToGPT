"""Real MCP Streamable HTTP probe: initialize → initialized → tools/list.

Exposes a single async entry point ``probe_mcp_endpoint()`` that performs a
complete MCP handshake and returns structured results.  No GET tricks, no
hardcoded tool lists.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.models.mcp import McpProbeResult, McpProbeStep

logger = logging.getLogger("garmintogpt.probe")

_INITIALIZE_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "garmin-mcp-local-probe", "version": "0.1.0"},
    },
}

_INITIALIZED_NOTIFICATION: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

_TOOLS_LIST_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {},
}

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


async def probe_mcp_endpoint(
    base_url: str,
    *,
    timeout_seconds: float = 10.0,
) -> McpProbeResult:
    """Run a full MCP probe against ``{base_url}/mcp``.

    Steps
    -----
    1. POST ``initialize`` – check ``Mcp-Session-Id`` header.
    2. POST ``notifications/initialized``.
    3. POST ``tools/list``.
    """
    mcp_url = f"{base_url.rstrip('/')}/mcp"
    steps: list[McpProbeStep] = []
    session_id: str | None = None
    result = McpProbeResult(ok=False, status="error", final_url=mcp_url)

    logger.info("MCP probe starting – target=%s", mcp_url)

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:

        # ── Step 1: initialize ──────────────────────────────────────────
        step_name = "initialize"
        t0 = time.perf_counter()
        try:
            resp = await client.post(mcp_url, json=_INITIALIZE_PAYLOAD, headers=MCP_HEADERS)
            elapsed = _ms_since(t0)
        except httpx.RequestError as exc:
            elapsed = _ms_since(t0)
            steps.append(_step(step_name, ok=False, duration_ms=elapsed, detail=str(exc)))
            result.error = f"HTTP request failed: {exc}"
            result.steps = steps
            logger.warning("MCP probe FAIL – %s – %s", mcp_url, exc)
            return result

        steps.append(
            _step(step_name, status_code=resp.status_code, ok=False, duration_ms=elapsed, detail="")
        )

        # Validate HTTP status
        if resp.status_code == 200:
            steps[-1].ok = True
            steps[-1].detail = "initialize returned HTTP 200"
        elif resp.status_code == 202:
            steps[-1].ok = True
            steps[-1].detail = "initialize returned HTTP 202 (accepted)"
        else:
            _fail_step(steps[-1], f"initialize returned HTTP {resp.status_code}")
            result.error = f"initialize: HTTP {resp.status_code} – {resp.text[:300]}"
            result.steps = steps
            logger.warning("MCP probe FAIL – initialize HTTP %d", resp.status_code)
            return result

        # Parse JSON-RPC response
        try:
            rpc_body = resp.json()
        except json.JSONDecodeError:
            _fail_step(steps[-1], "initialize: invalid JSON-RPC response (not JSON)")
            result.error = "initialize: response is not valid JSON"
            result.steps = steps
            return result

        if rpc_body.get("jsonrpc") != "2.0":
            _fail_step(steps[-1], "initialize: missing jsonrpc version field")
            result.error = "initialize: response missing jsonrpc 2.0"
            result.steps = steps
            return result

        if "error" in rpc_body:
            err = rpc_body["error"]
            _fail_step(steps[-1], f"initialize JSON-RPC error: {err.get('message', err)}")
            result.error = f"initialize JSON-RPC error: {err.get('message', err)}"
            result.steps = steps
            return result

        # Extract server info from result
        init_result = rpc_body.get("result", {})
        result.server_name = init_result.get("serverInfo", {}).get("name")
        result.server_version = init_result.get("serverInfo", {}).get("version")
        result.protocol_version = init_result.get("protocolVersion")

        # Check for Mcp-Session-Id header
        session_id = resp.headers.get("Mcp-Session-Id")
        if session_id:
            result.session_id = session_id
            steps[-1].detail += f" (session: {session_id[:16]}…)"

        logger.info(
            "MCP probe – initialize OK (server=%s v=%s proto=%s session=%s)",
            result.server_name,
            result.server_version,
            result.protocol_version,
            session_id,
        )

        # ── Step 2: notifications/initialized ────────────────────────────
        step_name = "notifications/initialized"
        t0 = time.perf_counter()
        headers = dict(MCP_HEADERS)
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        try:
            notif_resp = await client.post(mcp_url, json=_INITIALIZED_NOTIFICATION, headers=headers)
            elapsed = _ms_since(t0)
        except httpx.RequestError as exc:
            elapsed = _ms_since(t0)
            steps.append(_step(step_name, ok=False, duration_ms=elapsed, detail=str(exc)))
            result.error = f"notifications/initialized failed: {exc}"
            result.steps = steps
            return result

        notif_ok = notif_resp.status_code in (200, 202)
        steps.append(
            _step(
                step_name,
                status_code=notif_resp.status_code,
                ok=notif_ok,
                duration_ms=elapsed,
                detail=(
                    f"HTTP {notif_resp.status_code}"
                    + (" (accepted)" if notif_ok and notif_resp.status_code == 202 else "")
                ),
            )
        )

        # ── Step 3: tools/list ───────────────────────────────────────────
        step_name = "tools/list"
        t0 = time.perf_counter()

        try:
            tools_resp = await client.post(mcp_url, json=_TOOLS_LIST_PAYLOAD, headers=headers)
            elapsed = _ms_since(t0)
        except httpx.RequestError as exc:
            elapsed = _ms_since(t0)
            steps.append(_step(step_name, ok=False, duration_ms=elapsed, detail=str(exc)))
            result.error = f"tools/list failed: {exc}"
            result.steps = steps
            return result

        if tools_resp.status_code != 200:
            steps.append(
                _step(
                    step_name,
                    status_code=tools_resp.status_code,
                    ok=False,
                    duration_ms=elapsed,
                    detail=f"tools/list returned HTTP {tools_resp.status_code}",
                )
            )
            result.error = f"tools/list: HTTP {tools_resp.status_code}"
            result.steps = steps
            return result

        try:
            tools_body = tools_resp.json()
        except json.JSONDecodeError:
            steps.append(
                _step(
                    step_name, status_code=200, ok=False,
                    duration_ms=elapsed, detail="invalid JSON",
                )
            )
            result.error = "tools/list: response is not valid JSON"
            result.steps = steps
            return result

        if "error" in tools_body:
            err = tools_body["error"]
            steps.append(
                _step(
                    step_name,
                    status_code=200,
                    ok=False,
                    duration_ms=elapsed,
                    detail=f"tools/list JSON-RPC error: {err.get('message', err)}",
                )
            )
            result.error = f"tools/list JSON-RPC error: {err.get('message', err)}"
            result.steps = steps
            return result

        all_tools: list[dict] = tools_body.get("result", {}).get("tools", [])
        tools_count = len(all_tools)

        steps.append(
            _step(
                step_name,
                status_code=200,
                ok=True,
                duration_ms=elapsed,
                detail=f"found {tools_count} tool(s)",
            )
        )

        result.ok = True
        result.status = "ok"
        result.tools_count = tools_count
        result.tools = all_tools
        result.steps = steps

        logger.info(
            "MCP probe OK – %d tools found via %s",
            tools_count,
            mcp_url,
        )

        return result


def _step(
    method: str, *, ok: bool, duration_ms: int, detail: str,
    status_code: int | None = None,
) -> McpProbeStep:
    return McpProbeStep(
        method=method,
        status_code=status_code,
        ok=ok,
        duration_ms=duration_ms,
        detail=detail,
    )


def _fail_step(step: McpProbeStep, reason: str) -> None:
    step.ok = False
    step.detail = reason


def _ms_since(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
