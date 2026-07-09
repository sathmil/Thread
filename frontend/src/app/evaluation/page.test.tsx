import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getEvaluationRun: vi.fn(),
}));

import { getEvaluationRun } from "@/lib/api";

import EvaluationPage from "./page";

describe("EvaluationPage", () => {
  it("renders metric cards and the per-query results table", async () => {
    vi.mocked(getEvaluationRun).mockResolvedValue({
      run_id: "abc-123",
      embedding_model: "Local MiniLM",
      unit_type: "Passages",
      top_k: 3,
      recall_at_k: 0.857,
      mrr: 0.893,
      avg_latency_ms: 42.6,
      results: [
        {
          query: "feeling invisible at school",
          expected_story_ids: ["002", "003"],
          retrieved_story_ids: ["002", "001", "007"],
          hit_at_k: true,
          reciprocal_rank: 1,
          top_score: 0.56,
        },
      ],
    });

    renderWithQueryClient(<EvaluationPage />);

    expect(await screen.findByText("0.86")).toBeInTheDocument();
    expect(screen.getByText("0.89")).toBeInTheDocument();
    expect(screen.getByText("feeling invisible at school")).toBeInTheDocument();
    expect(screen.getByText("hit")).toBeInTheDocument();
  });
});
