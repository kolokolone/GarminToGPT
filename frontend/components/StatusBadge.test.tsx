import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the French label for running", () => {
    render(<StatusBadge state="running" />);
    expect(screen.getByText("actif")).toBeInTheDocument();
  });
});
