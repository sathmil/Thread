import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getProjection: vi.fn(),
  getJourney: vi.fn(),
}));

import { getProjection } from "@/lib/api";

import HomePage from "./page";

describe("HomePage (explore map)", () => {
  it("renders the heading, fetches projection data, and shows map controls", async () => {
    vi.mocked(getProjection).mockResolvedValue([
      {
        external_id: "001",
        story_uuid: "11111111-1111-1111-1111-111111111111",
        title: "A story",
        preview: "Once upon a time...",
        x: 0.1,
        y: 0.2,
        cluster_label: 0,
        theme_name: "Voice",
      },
    ]);

    renderWithQueryClient(<HomePage />);

    expect(await screen.findByText("Find yourself in someone else's experience")).toBeInTheDocument();
    expect(getProjection).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset view" })).toBeDisabled();
  });

  it("shows an empty state when there are no stories to plot", async () => {
    vi.mocked(getProjection).mockResolvedValue([]);

    renderWithQueryClient(<HomePage />);

    expect(await screen.findByText("No stories to plot yet.")).toBeInTheDocument();
  });

  it("filters points via the search box without requiring a submit", async () => {
    vi.mocked(getProjection).mockResolvedValue([
      {
        external_id: "001",
        story_uuid: "11111111-1111-1111-1111-111111111111",
        title: "A story about belonging",
        preview: "Once upon a time...",
        x: 0.1,
        y: 0.2,
        cluster_label: 0,
        theme_name: "Voice",
      },
    ]);

    renderWithQueryClient(<HomePage />);
    await screen.findByRole("button", { name: "Zoom in" });

    const input = screen.getByPlaceholderText(/belonging, identity/i);
    expect(input).toHaveValue("");
  });
});
