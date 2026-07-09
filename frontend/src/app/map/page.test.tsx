import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getProjection: vi.fn(),
}));

import { getProjection } from "@/lib/api";

import MapPage from "./page";

describe("MapPage", () => {
  it("renders the heading and fetches projection data", async () => {
    vi.mocked(getProjection).mockResolvedValue([
      {
        external_id: "001",
        title: "A story",
        preview: "Once upon a time...",
        x: 0.1,
        y: 0.2,
        cluster_label: 0,
        theme_name: "Voice",
      },
    ]);

    renderWithQueryClient(<MapPage />);

    expect(await screen.findByText("Embedding map")).toBeInTheDocument();
    expect(getProjection).toHaveBeenCalled();
  });

  it("shows an empty state when there are no stories to plot", async () => {
    vi.mocked(getProjection).mockResolvedValue([]);

    renderWithQueryClient(<MapPage />);

    expect(await screen.findByText("No stories to plot yet.")).toBeInTheDocument();
  });
});
