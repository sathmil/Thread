import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getStories: vi.fn(),
  search: vi.fn(),
}));

import { getStories, search } from "@/lib/api";

import SearchPage from "./page";

describe("SearchPage", () => {
  it("shows the fallback story list when no query has been submitted", async () => {
    vi.mocked(getStories).mockResolvedValue([
      {
        external_id: "001",
        title: "A story about belonging",
        focus: "Belonging & Community",
        word_count: 100,
        preview: "Once upon a time...",
      },
    ]);

    renderWithQueryClient(<SearchPage />);

    expect(await screen.findByText("Story 001")).toBeInTheDocument();
    expect(screen.getByText("Belonging & Community")).toBeInTheDocument();
  });

  it("renders search results after submitting a query", async () => {
    vi.mocked(getStories).mockResolvedValue([]);
    vi.mocked(search).mockResolvedValue({
      query: "feeling invisible at school",
      unit: "Passages",
      results: [
        {
          story_id: "002",
          unit_type: "passage",
          unit_index: 2,
          text_unit: "Then we get to school, and suddenly it's like we disappear.",
          preview: "Then we get to school, and suddenly it's like we disappear.",
          score: 0.56,
          theme: "Read, Know, School, Doesn",
        },
      ],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<SearchPage />);
    const input = screen.getByPlaceholderText(/belonging, identity/i);

    await user.type(input, "feeling invisible at school");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(search).toHaveBeenCalledWith({
      query: "feeling invisible at school",
      unit: "Passages",
      top_k: 5,
    }));

    expect(await screen.findByText(/0.56 similarity/)).toBeInTheDocument();
  });
});
