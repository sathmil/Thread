import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getClusters: vi.fn(),
}));

import { getClusters } from "@/lib/api";

import ClustersPage from "./page";

describe("ClustersPage", () => {
  it("renders theme cards with summaries and member stories", async () => {
    vi.mocked(getClusters).mockResolvedValue([
      {
        cluster_label: 0,
        theme_name: "Voice, School",
        summary: "These stories cluster around belonging.",
        summary_source: "rule_based",
        stories: [
          {
            external_id: "001",
            title: "A story about belonging",
            focus: "Belonging & Community",
            word_count: 100,
            preview: "Once upon a time...",
          },
        ],
      },
    ]);

    renderWithQueryClient(<ClustersPage />);

    expect(await screen.findByText("Theme 0: Voice, School")).toBeInTheDocument();
    expect(screen.getByText("These stories cluster around belonging.")).toBeInTheDocument();
    expect(screen.getByText("Story 001")).toBeInTheDocument();
  });
});
