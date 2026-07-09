import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getStories: vi.fn(),
}));

import { getStories } from "@/lib/api";

import DatasetPage from "./page";

describe("DatasetPage", () => {
  it("renders one row per story", async () => {
    vi.mocked(getStories).mockResolvedValue([
      {
        external_id: "001",
        title: "A story about belonging",
        focus: "Belonging & Community",
        word_count: 100,
        preview: "Once upon a time...",
      },
      {
        external_id: "002",
        title: "A story about school",
        focus: "Education & Access",
        word_count: 120,
        preview: "Every morning...",
      },
    ]);

    renderWithQueryClient(<DatasetPage />);

    expect(await screen.findByText("A story about belonging")).toBeInTheDocument();
    expect(screen.getByText("A story about school")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3); // header + 2 stories
  });
});
