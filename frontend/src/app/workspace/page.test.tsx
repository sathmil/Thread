import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getDatasets: vi.fn(),
  createDataset: vi.fn(),
  uploadStories: vi.fn(),
  indexDataset: vi.fn(),
  reindexDataset: vi.fn(),
  getJob: vi.fn(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@clerk/nextjs";

import { getDatasets, getJob, indexDataset, reindexDataset } from "@/lib/api";

import WorkspacePage from "./page";

afterEach(() => {
  vi.unstubAllEnvs();
});

function mockSignedIn() {
  vi.mocked(useAuth).mockReturnValue({
    isSignedIn: true,
    getToken: vi.fn().mockResolvedValue("fake-token"),
  } as unknown as ReturnType<typeof useAuth>);
}

describe("WorkspacePage", () => {
  it("shows a not-configured message when Clerk keys are absent", () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "");

    renderWithQueryClient(<WorkspacePage />);

    expect(screen.getByText(/isn't configured/)).toBeInTheDocument();
  });

  it("lists datasets and shows the create-dataset form for signed-in users", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    mockSignedIn();
    vi.mocked(getDatasets).mockResolvedValue([
      {
        id: "1",
        name: "WHO WE ARE (seed)",
        description: null,
        visibility: "public",
        status: "ready",
        owner_user_id: null,
      },
    ]);

    renderWithQueryClient(<WorkspacePage />);

    expect(await screen.findByText("WHO WE ARE (seed)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Dataset name")).toBeInTheDocument();
  });

  it("prompts signed-out users to sign in instead of showing the create form", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    vi.mocked(useAuth).mockReturnValue({
      isSignedIn: false,
      getToken: vi.fn().mockResolvedValue(null),
    } as unknown as ReturnType<typeof useAuth>);
    vi.mocked(getDatasets).mockResolvedValue([]);

    renderWithQueryClient(<WorkspacePage />);

    expect(await screen.findByText(/Sign in to create your own private datasets/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Dataset name")).not.toBeInTheDocument();
  });

  it("shows upload/index controls for a private (owned) dataset, and polls job status", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    mockSignedIn();
    vi.mocked(getDatasets).mockResolvedValue([
      {
        id: "ds-1",
        name: "My private dataset",
        description: null,
        visibility: "private",
        status: "draft",
        owner_user_id: "user-a",
      },
    ]);
    vi.mocked(indexDataset).mockResolvedValue({
      id: "job-1",
      dataset_id: "ds-1",
      job_type: "index",
      status: "succeeded",
      progress_pct: 100,
      story_count: 5,
      duration_ms: 120,
      embedding_ms: 80,
      avg_embedding_ms_per_story: 16,
      error_message: null,
      warning_message: null,
    });
    vi.mocked(getJob).mockResolvedValue({
      id: "job-1",
      dataset_id: "ds-1",
      job_type: "index",
      status: "succeeded",
      progress_pct: 100,
      story_count: 5,
      duration_ms: 120,
      embedding_ms: 80,
      avg_embedding_ms_per_story: 16,
      error_message: null,
      warning_message: null,
    });

    const user = userEvent.setup();
    renderWithQueryClient(<WorkspacePage />);

    expect(await screen.findByText("My private dataset")).toBeInTheDocument();
    const indexButton = screen.getByRole("button", { name: "Index" });

    await user.click(indexButton);

    expect(await screen.findByText(/Indexed 5 stories/)).toBeInTheDocument();
  });

  it("shows a warning message after re-indexing falls back to a different provider", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    mockSignedIn();
    vi.mocked(getDatasets).mockResolvedValue([
      {
        id: "ds-1",
        name: "My private dataset",
        description: null,
        visibility: "private",
        status: "ready",
        owner_user_id: "user-a",
      },
    ]);
    const jobWithWarning = {
      id: "job-2",
      dataset_id: "ds-1",
      job_type: "reindex",
      status: "succeeded" as const,
      progress_pct: 100,
      story_count: 5,
      duration_ms: 90,
      embedding_ms: 40,
      avg_embedding_ms_per_story: 8,
      error_message: null,
      warning_message: "OPENAI_API_KEY is not set — used Local MiniLM instead of OpenAI API.",
    };
    vi.mocked(reindexDataset).mockResolvedValue(jobWithWarning);
    vi.mocked(getJob).mockResolvedValue(jobWithWarning);

    const user = userEvent.setup();
    renderWithQueryClient(<WorkspacePage />);

    expect(await screen.findByText("My private dataset")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Re-index (OpenAI)" }));

    expect(await screen.findByText(/used Local MiniLM instead of OpenAI API/)).toBeInTheDocument();
  });

  it("does not show upload/index controls for public datasets", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    mockSignedIn();
    vi.mocked(getDatasets).mockResolvedValue([
      {
        id: "public-1",
        name: "WHO WE ARE (seed)",
        description: null,
        visibility: "public",
        status: "ready",
        owner_user_id: null,
      },
    ]);

    renderWithQueryClient(<WorkspacePage />);

    expect(await screen.findByText("WHO WE ARE (seed)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Index" })).not.toBeInTheDocument();
  });
});
