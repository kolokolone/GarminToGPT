import type {
  ActionResult,
  GarminAuthResult,
  GarminAuthStatus,
  GlobalStatus,
  LogResult,
  McpLocalStatus,
  TestDefinition,
  TestResult,
  TunnelStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown; message?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
      else if (typeof parsed.message === "string") message = parsed.message;
    } catch {
      // Keep the raw body when Garmin/API did not return JSON.
    }
    throw new Error(message || `Erreur API ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  startAccess: () => request<GlobalStatus>("/api/access/start", { method: "POST" }),
  stopAccess: () => request<GlobalStatus>("/api/access/stop", { method: "POST" }),
  status: () => request<GlobalStatus>("/api/status"),
  authStatus: () => request<GarminAuthStatus>("/api/auth/status"),
  configureKey: (payload: { api_key: string; expires_on?: string | null }) =>
    request<GarminAuthResult>("/api/auth/key", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateKeyExpiration: (expires_on: string | null) =>
    request<GarminAuthStatus>("/api/auth/key", {
      method: "PATCH",
      body: JSON.stringify({ expires_on }),
    }),
  removeKey: () =>
    request<GarminAuthResult>("/api/auth/key", {
      method: "DELETE",
      body: JSON.stringify({ confirm: true }),
    }),
  verifyAuth: () => request<GarminAuthStatus>("/api/auth/verify", { method: "POST" }),
  mcpLocalStatus: () => request<McpLocalStatus>("/api/mcp/status"),
  startMcp: () => request<McpLocalStatus>("/api/mcp/start", { method: "POST" }),
  stopMcp: () => request<McpLocalStatus>("/api/mcp/stop", { method: "POST" }),
  restartMcp: () => request<McpLocalStatus>("/api/mcp/restart", { method: "POST" }),
  tunnelStatus: () => request<TunnelStatus>("/api/tunnel/status"),
  startTunnel: () => request<ActionResult>("/api/tunnel/start", { method: "POST" }),
  stopTunnel: () => request<ActionResult>("/api/tunnel/stop", { method: "POST" }),
  pauseTunnel: () => request<ActionResult>("/api/tunnel/pause", { method: "POST" }),
  resumeTunnel: () => request<ActionResult>("/api/tunnel/resume", { method: "POST" }),
  regenerateTunnel: () => request<ActionResult>("/api/tunnel/regenerate", { method: "POST" }),
  logs: (service: string) => request<LogResult>(`/api/logs/${service}`),
  tests: () => request<{ tests: TestDefinition[] }>("/api/tests"),
  runTest: (id: string) => request<TestResult>(`/api/tests/${id}/run`, { method: "POST" }),
  runAllTests: () => request<{ results: TestResult[] }>("/api/tests/run-all", { method: "POST" }),
};
