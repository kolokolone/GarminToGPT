import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TunnelCard } from "./TunnelCard";

describe("TunnelCard", () => {
  it("allows copying the ChatGPT MCP URL", () => {
    const onCopy = vi.fn();
    render(
      <TunnelCard
        tunnel={{
          state: "running",
          mode: "quick",
          public_url: "https://abc.trycloudflare.com",
          chatgpt_mcp_url: "https://abc.trycloudflare.com/mcp",
          pid: 42,
          last_event: "ok",
          process: { status: "running", pid: 42, message: "ok" },
        }}
        loading={false}
        copied={false}
        onCopy={onCopy}
        onStart={vi.fn()}
        onStop={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Copier" }));

    expect(onCopy).toHaveBeenCalledOnce();
  });
});
