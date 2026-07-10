import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getEvaluationRun: vi.fn(),
  getEvaluationRuns: vi.fn(),
  getEvaluationRunDetail: vi.fn(),
}));

import { getEvaluationRun, getEvaluationRuns } from "@/lib/api";

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
      precision_at_k: 0.333,
      avg_latency_ms: 42.6,
      created_at: "2026-07-10T12:00:00Z",
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
    vi.mocked(getEvaluationRuns).mockResolvedValue([]);

    renderWithQueryClient(<EvaluationPage />);

    expect(await screen.findByText("0.86")).toBeInTheDocument();
    expect(screen.getByText("0.89")).toBeInTheDocument();
    expect(screen.getByText("0.33")).toBeInTheDocument();
    expect(screen.getByText("feeling invisible at school")).toBeInTheDocument();
    expect(screen.getByText("hit")).toBeInTheDocument();
  });

  it("shows saved runs in the history table and loads one on click", async () => {
    vi.mocked(getEvaluationRun).mockResolvedValue({
      run_id: "abc-123",
      embedding_model: "Local MiniLM",
      unit_type: "Passages",
      top_k: 3,
      recall_at_k: 0.857,
      mrr: 0.893,
      precision_at_k: 0.333,
      avg_latency_ms: 42.6,
      created_at: "2026-07-10T12:00:00Z",
      results: [],
    });
    vi.mocked(getEvaluationRuns).mockResolvedValue([
      {
        run_id: "run-1",
        embedding_model: "OpenAI API",
        unit_type: "Passages",
        top_k: 3,
        recall_at_k: 0.9,
        mrr: 0.95,
        precision_at_k: 0.4,
        avg_latency_ms: 30,
        created_at: "2026-07-09T12:00:00Z",
      },
    ]);

    renderWithQueryClient(<EvaluationPage />);

    expect(await screen.findByText("OpenAI API")).toBeInTheDocument();
  });
});
