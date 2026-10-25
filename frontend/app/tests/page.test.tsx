import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TestResult } from "../../lib/types";
import TestsPage from "./page";

const CONFIG_TEST = {
  id: "check_config",
  name: "Configuration chargée",
  description: "Valide la configuration.",
};

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

describe("TestsPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads and displays available tests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ tests: [CONFIG_TEST] })),
    );

    render(<TestsPage />);

    await waitFor(() => expect(screen.getByText("Configuration chargée")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Lancer tous les tests" })).toBeInTheDocument();
  });

  it("groups current Garmin, tunnel and smoke tests under their own sections", async () => {
    const tests = [
      CONFIG_TEST,
      {
        id: "check_garmin_api_key",
        name: "Clé API Garmin détectée",
        description: "Cherche la clé Garmin.",
      },
      {
        id: "check_tunnel_ready",
        name: "Tunnel OpenAI prêt",
        description: "Vérifie /readyz.",
      },
      {
        id: "full_smoke_test",
        name: "Smoke test complet",
        description: "Vérifie les prérequis.",
      },
    ];
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ tests })));

    render(<TestsPage />);

    await waitFor(() => expect(screen.getByText("Clé API Garmin détectée")).toBeInTheDocument());
    expect(screen.getByText("GARMIN")).toBeInTheDocument();
    expect(screen.getByText("TUNNEL OPENAI")).toBeInTheDocument();
    expect(screen.getByText("SMOKE TEST")).toBeInTheDocument();
  });

  it("runs a test and shows its message, duration and suggestion", async () => {
    const result: TestResult = {
      id: "check_config",
      name: "Configuration chargée",
      state: "failed",
      duration_ms: 12,
      message: "Configuration incomplète.",
      suggestion: "Corrige config/app.yaml.",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/tests")) return jsonResponse({ tests: [CONFIG_TEST] });
        if (url.endsWith("/api/tests/check_config/run") && init?.method === "POST") {
          return jsonResponse(result);
        }
        throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
      }),
    );

    render(<TestsPage />);

    await screen.findByText("Configuration chargée");
    fireEvent.click(screen.getByRole("button", { name: "Lancer" }));

    await waitFor(() => expect(screen.getByText(/Configuration incomplète/)).toBeInTheDocument());
    expect(screen.getByText(/12 ms/)).toBeInTheDocument();
    expect(screen.getByText(/Suggestion : Corrige config\/app\.yaml\./)).toBeInTheDocument();
  });
});
