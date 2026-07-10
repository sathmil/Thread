import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getDatasets: vi.fn(),
  getInsights: vi.fn(),
}));

import { getDatasets, getInsights } from "@/lib/api";

import InsightsPage from "./page";

describe("InsightsPage", () => {
  it("groups correlation and superlative findings into separate sections", async () => {
    vi.mocked(getDatasets).mockResolvedValue([
      { id: "dataset-1", name: "WHO WE ARE (seed)", description: null, visibility: "public", status: "ready", owner_user_id: null },
    ]);
    vi.mocked(getInsights).mockResolvedValue([
      {
        finding_type: "correlation",
        finding_text: "Stories that score high on belonging are also score high on agency (r=0.91 across 10 stories).",
        dimension_a: "belonging",
        dimension_b: "agency",
        effect_size: 0.91,
        sample_size: 10,
        subject_story_external_id: null,
        subject_story_uuid: null,
        subject_story_title: null,
      },
      {
        finding_type: "most_unique",
        finding_text: '"You learn to translate everything." is the most unique story in this dataset.',
        dimension_a: null,
        dimension_b: null,
        effect_size: 0.83,
        sample_size: 10,
        subject_story_external_id: "009",
        subject_story_uuid: "7089c9d2-7b05-4e7c-8e4a-7ed0544876ce",
        subject_story_title: "You learn to translate everything.",
      },
    ]);

    renderWithQueryClient(<InsightsPage />);

    expect(await screen.findByText("Patterns across dimensions")).toBeInTheDocument();
    expect(screen.getByText("Notable stories")).toBeInTheDocument();
    expect(screen.getByText("r = 0.91")).toBeInTheDocument();
    expect(screen.getByText("Most unique")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /You learn to translate everything/ })).toHaveAttribute(
      "href",
      "/stories/7089c9d2-7b05-4e7c-8e4a-7ed0544876ce"
    );
  });

  it("shows an empty state when there are no findings yet", async () => {
    vi.mocked(getDatasets).mockResolvedValue([
      { id: "dataset-1", name: "WHO WE ARE (seed)", description: null, visibility: "public", status: "ready", owner_user_id: null },
    ]);
    vi.mocked(getInsights).mockResolvedValue([]);

    renderWithQueryClient(<InsightsPage />);

    expect(await screen.findByText(/Not enough data yet/)).toBeInTheDocument();
  });
});
