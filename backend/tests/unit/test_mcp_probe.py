"""Tests for MCP probe session cleanup."""

import asyncio
import logging
from collections.abc import Iterator

import httpx
from app.services import mcp_probe_service


class _FakeAsyncClient:
    responses: Iterator[httpx.Response | httpx.HTTPError]
    calls: list[tuple[str, str, dict[str, str]]]

    def __init__(self, *, timeout: httpx.Timeout) -> None:
        del timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        del json
        self.calls.append(("POST", url, headers))
        return self._next_response()

    async def delete(self, url: str, *, headers: dict[str, str]) -> httpx.Response:
        self.calls.append(("DELETE", url, headers))
        return self._next_response()

    def _next_response(self) -> httpx.Response:
        response = next(self.responses)
        if isinstance(response, httpx.HTTPError):
            raise response
        return response


def _response(
    status_code: int,
    *,
    json: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json,
        headers=headers,
        request=httpx.Request("POST", "http://127.0.0.1:8080/mcp"),
    )


def _initialize_response(*, valid_json: bool = True) -> httpx.Response:
    if not valid_json:
        return httpx.Response(
            200,
            content=b"not-json",
            headers={"Mcp-Session-Id": "session-123"},
            request=httpx.Request("POST", "http://127.0.0.1:8080/mcp"),
        )
    return _response(
        200,
        json={
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "garmin-mcp", "version": "1.0.0"},
            },
        },
        headers={"Mcp-Session-Id": "session-123"},
    )


def _install_fake_client(
    monkeypatch,
    responses: list[httpx.Response | httpx.HTTPError],
) -> list[tuple[str, str, dict[str, str]]]:
    calls: list[tuple[str, str, dict[str, str]]] = []
    _FakeAsyncClient.responses = iter(responses)
    _FakeAsyncClient.calls = calls
    monkeypatch.setattr(mcp_probe_service.httpx, "AsyncClient", _FakeAsyncClient)
    return calls


def test_probe_closes_session_after_success(monkeypatch) -> None:
    calls = _install_fake_client(
        monkeypatch,
        [
            _initialize_response(),
            _response(202),
            _response(200, json={"jsonrpc": "2.0", "result": {"tools": []}}),
            _response(204),
        ],
    )

    result = asyncio.run(mcp_probe_service.probe_mcp_endpoint("http://127.0.0.1:8080"))

    assert result.ok is True
    assert [method for method, _, _ in calls] == ["POST", "POST", "POST", "DELETE"]
    assert calls[-1][1] == "http://127.0.0.1:8080/mcp"
    assert calls[-1][2]["Mcp-Session-Id"] == "session-123"


def test_probe_closes_session_on_early_return(monkeypatch) -> None:
    calls = _install_fake_client(
        monkeypatch,
        [
            _initialize_response(valid_json=False),
            _response(204),
        ],
    )

    result = asyncio.run(mcp_probe_service.probe_mcp_endpoint("http://127.0.0.1:8080"))

    assert result.ok is False
    assert result.error == "initialize: response is not valid JSON"
    assert [method for method, _, _ in calls] == ["POST", "DELETE"]


def test_probe_ignores_session_cleanup_failure(monkeypatch, caplog) -> None:
    cleanup_error = httpx.ConnectError(
        "connection lost",
        request=httpx.Request("DELETE", "http://127.0.0.1:8080/mcp"),
    )
    calls = _install_fake_client(
        monkeypatch,
        [
            _initialize_response(),
            _response(202),
            _response(200, json={"jsonrpc": "2.0", "result": {"tools": []}}),
            cleanup_error,
        ],
    )

    with caplog.at_level(logging.WARNING, logger="GarminToGPT.probe"):
        result = asyncio.run(mcp_probe_service.probe_mcp_endpoint("http://127.0.0.1:8080"))

    assert result.ok is True
    assert calls[-1][0] == "DELETE"
    assert "session cleanup failed" in caplog.text


def test_probe_ignores_unexpected_cleanup_status(monkeypatch, caplog) -> None:
    _install_fake_client(
        monkeypatch,
        [
            _initialize_response(),
            _response(202),
            _response(200, json={"jsonrpc": "2.0", "result": {"tools": []}}),
            _response(500),
        ],
    )

    with caplog.at_level(logging.WARNING, logger="GarminToGPT.probe"):
        result = asyncio.run(mcp_probe_service.probe_mcp_endpoint("http://127.0.0.1:8080"))

    assert result.ok is True
    assert "session cleanup returned HTTP 500" in caplog.text
