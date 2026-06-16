import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TestsPage from "./page";

describe("TestsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads and displays available tests", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ tests: [{ id: "check_config", name: "Configuration chargée", description: "Valide la configuration." }] }),
    })));

    render(<TestsPage />);

    await waitFor(() => expect(screen.getByText("Configuration chargée")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Lancer tous les tests" })).toBeInTheDocument();
  });
});
