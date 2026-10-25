import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  TunnelConfigResult,
  TunnelConfigStatus,
  TunnelStatus,
} from "../../lib/types";
import TunnelPage from "./page";

const TUNNEL_ID = "tunnel_0123456789abcdef0123456789abcdef";
const API_KEY = "sk-runtime-secret-1234567890";

const NOT_CONFIGURED: TunnelConfigStatus = {
  configured: false,
  tunnel_id: null,
  key_hint: null,
  source: "none",
  key_source: null,
  tunnel_id_source: null,
  editable: true,
  binary_installed: false,
  binary_version: null,
  message: "Tunnel OpenAI non configuré.",
};

const CONFIGURED: TunnelConfigStatus = {
  configured: true,
  tunnel_id: TUNNEL_ID,
  key_hint: "••••7890",
  source: "file",
  key_source: "file",
  tunnel_id_source: "file",
  editable: true,
  binary_installed: true,
  binary_version: "0.0.18",
  message: "Tunnel OpenAI configuré.",
};

const STOPPED: TunnelStatus = {
  state: "stopped",
  provider: "openai",
  configured: false,
  tunnel_id: null,
  api_key_configured: false,
  binary_installed: false,
  binary_version: null,
  ready: false,
  health_status: null,
  health_url: null,
  ui_url: null,
  connector_url: "https://chatgpt.com/#settings/Connectors",
  pid: null,
  last_event: "Tunnel OpenAI non configuré.",
  process: { status: "stopped", pid: null, message: "" },
};

const RUNNING: TunnelStatus = {
  ...STOPPED,
  state: "running",
  configured: true,
  tunnel_id: TUNNEL_ID,
  api_key_configured: true,
  binary_installed: true,
  binary_version: "0.0.18",
  ready: true,
  health_status: 200,
  health_url: "http://127.0.0.1:8091/readyz",
  ui_url: "http://127.0.0.1:8091/ui",
  last_event: "Tunnel OpenAI prêt.",
  process: { status: "running", pid: 42, message: "running" },
};

const RESULT: TunnelConfigResult = {
  ok: true,
  changed: true,
  message: "Tunnel OpenAI validé et enregistré.",
  config: CONFIGURED,
  status: RUNNING,
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

describe("TunnelPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("validates and saves the tunnel ID and runtime key without rendering the secret", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/tunnel/config") && (!init || init.method === undefined)) {
        return jsonResponse(NOT_CONFIGURED);
      }
      if (url.endsWith("/api/tunnel/status")) {
        return jsonResponse(STOPPED);
      }
      if (url.endsWith("/api/tunnel/config") && init?.method === "POST") {
        return jsonResponse(RESULT);
      }
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<TunnelPage />);

    const idInput = await screen.findByLabelText("Tunnel ID");
    const keyInput = screen.getByLabelText("Runtime API key OpenAI");
    fireEvent.change(idInput, { target: { value: TUNNEL_ID } });
    fireEvent.change(keyInput, { target: { value: API_KEY } });
    fireEvent.click(screen.getByRole("button", { name: "Tester et enregistrer" }));

    await waitFor(() =>
      expect(screen.getByText("Tunnel OpenAI validé et enregistré.")).toBeInTheDocument(),
    );
    expect(screen.getByText(TUNNEL_ID)).toBeInTheDocument();
    expect(screen.getByText("••••7890")).toBeInTheDocument();
    expect(screen.queryByText(API_KEY)).not.toBeInTheDocument();

    const saved = JSON.parse(String((fetchMock.mock.calls[2][1] as RequestInit).body));
    expect(saved.tunnel_id).toBe(TUNNEL_ID);
    expect(saved.api_key).toBe(API_KEY);
  });

  it("explains that environment-managed configuration is read-only", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/tunnel/config")) {
          return jsonResponse({
            ...CONFIGURED,
            source: "env",
            key_source: "env",
            tunnel_id_source: "env",
            editable: false,
          });
        }
        if (url.endsWith("/api/tunnel/status")) return jsonResponse(RUNNING);
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    render(<TunnelPage />);

    expect(
      await screen.findByText(/configuré par l.environnement/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tester et enregistrer" })).not.toBeInTheDocument();
  });
});
