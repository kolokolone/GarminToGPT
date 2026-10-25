import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GarminAuthResult, GarminAuthStatus } from "../../lib/types";
import ConnexionPage from "./page";

const KEY = "GCDC_" + "a".repeat(120);

const NOT_CONFIGURED: GarminAuthStatus = {
  state: "not_configured",
  configured: false,
  key: { source: null, hint: null, fingerprint: null },
  token_present: false,
  token_valid: false,
  token_expires_at: null,
  token_scopes: [],
  rotation: { expires_on: null, days_remaining: null, source: "unknown", warning: false },
  last_verified_at: null,
  display_name: null,
  message: "Aucune clé API Garmin configurée.",
  error: null,
};

const VALID: GarminAuthStatus = {
  state: "valid",
  configured: true,
  key: { source: "file", hint: "••••abcd", fingerprint: "0123456789ab" },
  token_present: true,
  token_valid: true,
  token_expires_at: "2026-10-26T12:00:00+00:00",
  token_scopes: ["CONNECT_READ", "PERSONAL_API_WELLNESS_READ"],
  rotation: {
    expires_on: "2026-11-24",
    days_remaining: 30,
    source: "declared",
    warning: false,
  },
  last_verified_at: "2026-10-25T12:00:00+00:00",
  display_name: "Test Runner",
  message: "Clé API valide; accès Garmin Connect opérationnel.",
  error: null,
};

const RESULT: GarminAuthResult = {
  ok: true,
  changed: true,
  message: "Clé API Garmin mise à jour et vérifiée.",
  status: VALID,
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

describe("ConnexionPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("saves a pasted key and never renders the full secret", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/auth/status")) {
        return jsonResponse(NOT_CONFIGURED);
      }
      if (url.endsWith("/api/auth/key") && init?.method === "POST") {
        return jsonResponse(RESULT);
      }
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ConnexionPage />);

    const input = await screen.findByLabelText("Clé API Garmin");
    fireEvent.change(input, { target: { value: KEY } });
    fireEvent.click(screen.getByRole("button", { name: "Tester et enregistrer" }));

    await waitFor(() =>
      expect(screen.getByText("Clé API Garmin mise à jour et vérifiée.")).toBeInTheDocument(),
    );
    expect(screen.getByText("••••abcd")).toBeInTheDocument();
    expect(screen.queryByText(KEY)).not.toBeInTheDocument();

    const saved = JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body));
    expect(saved.api_key).toBe(KEY);
  });

  it("shows an expired key with an actionable message", async () => {
    const expired: GarminAuthStatus = {
      ...VALID,
      state: "expired",
      token_valid: false,
      message: "Clé API Garmin refusée (invalide, révoquée ou expirée).",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/auth/status")) return jsonResponse(expired);
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    render(<ConnexionPage />);

    expect(
      await screen.findByText("Clé API Garmin refusée (invalide, révoquée ou expirée)."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mettre à jour la clé" })).toBeInTheDocument();
  });
});
