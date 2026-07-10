import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  askQuestion: vi.fn(),
}));

import { askQuestion } from "@/lib/api";

import AskPage from "./page";

describe("AskPage", () => {
  it("shows the graceful unavailable message when no OpenAI key is configured", async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      available: false,
      answer: "Conversational exploration needs an OpenAI key configured — try Search or Themes instead.",
      tool_calls: [],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AskPage />);

    const input = screen.getByPlaceholderText(/what themes usually appear/i);
    await user.type(input, "What themes usually appear alongside belonging?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(askQuestion).toHaveBeenCalledWith("What themes usually appear alongside belonging?"));

    expect(await screen.findByText("Not configured")).toBeInTheDocument();
    expect(screen.getByText(/needs an OpenAI key configured/)).toBeInTheDocument();
  });

  it("shows which tools were used when an answer is available", async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      available: true,
      answer: "Belonging often shows up alongside family and identity in this collection.",
      tool_calls: [{ tool: "search_stories", arguments: { query: "belonging" } }],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AskPage />);

    await user.type(screen.getByPlaceholderText(/what themes usually appear/i), "What goes with belonging?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText(/Belonging often shows up/)).toBeInTheDocument();
    expect(screen.getByText(/Used: search_stories/)).toBeInTheDocument();
    expect(screen.queryByText("Not configured")).not.toBeInTheDocument();
  });
});
