import type {
  ActionResult,
  GarminAuthResult,
  GarminAuthStatus,
  GlobalStatus,
  LogResult,
  McpLocalStatus,
  McpStatus,
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
    throw new Error(`Erreur API ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  status: () => request<GlobalStatus>("/api/status"),
  authStatus: () => request<GarminAuthStatus>("/api/auth/status"),
  login: (payload: { email?: string; password?: string; otp?: string }) =>
    request<GarminAuthResult>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  verifyAuth: () => request<GarminAuthStatus>("/api/auth/verify", { method: "POST" }),
  reauthenticate: () => request<GarminAuthResult>("/api/auth/reauthenticate", { method: "POST" }),
  disconnect: () => request<{ ok: boolean; message: string }>("/api/auth/disconnect", { method: "POST", body: JSON.stringify({ confirm: true }) }),
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
