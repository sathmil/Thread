import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "11111111-1111-1111-1111-111111111111" }),
}));

vi.mock("@/lib/api", () => ({
  getStoryDetail: vi.fn(),
  getJourney: vi.fn(),
  getFingerprint: vi.fn(),
}));

import { getFingerprint, getJourney, getStoryDetail } from "@/lib/api";

import StoryDetailPage from "./page";

describe("StoryDetailPage", () => {
  it("renders the story, its journey, and reveals the fingerprint behind the curious toggle", async () => {
    vi.mocked(getStoryDetail).mockResolvedValue({
      external_id: "001",
      title: "A story about belonging",
      focus: "Belonging & Community",
      story_text: "I found my community after joining the debate team.",
      word_count: 100,
      theme_name: "Belonging, Voice",
    });

    vi.mocked(getJourney).mockResolvedValue({
      nearest: [
        {
          story_id: "002",
          title: "A story about family",
          preview: "My grandmother taught me...",
          score: 0.82,
          same_theme: true,
          explanation: "Both score high on belonging and family.",
        },
      ],
      contrasting: {
        story_id: "003",
        title: "A story about grief",
        preview: "After the loss, I grieved quietly.",
        score: 0.12,
        same_theme: false,
        explanation: "This story leans toward grief while the first leans toward hope.",
      },
      reflection_questions: ["When did you last feel like you belonged somewhere?"],
    });

    vi.mocked(getFingerprint).mockResolvedValue({
      dimensions: { hope: 0.8, isolation: 0.1, identity: 0.6, family: 0.4, growth: 0.5, grief: 0.1, belonging: 0.9, agency: 0.7 },
      source: "rule_based",
      model: "keyword-heuristic-v1",
    });

    renderWithQueryClient(<StoryDetailPage />);

    expect(await screen.findByText("A story about belonging")).toBeInTheDocument();
    expect(screen.getByText("Belonging, Voice")).toBeInTheDocument();
    expect(screen.getByText("A story about family")).toBeInTheDocument();
    expect(screen.getByText("Both score high on belonging and family.")).toBeInTheDocument();
    expect(screen.getByText("A story about grief")).toBeInTheDocument();
    expect(screen.getByText("When did you last feel like you belonged somewhere?")).toBeInTheDocument();

    expect(screen.queryByText(/keyword-heuristic-v1/)).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /curious/i }));

    await waitFor(() => expect(getFingerprint).toHaveBeenCalled());
    expect(await screen.findByText(/keyword-heuristic-v1/)).toBeInTheDocument();
  });
});
