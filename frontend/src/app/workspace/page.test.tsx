import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  getDatasets: vi.fn(),
  createDataset: vi.fn(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@clerk/nextjs";

import { getDatasets } from "@/lib/api";

import WorkspacePage from "./page";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("WorkspacePage", () => {
  it("shows a not-configured message when Clerk keys are absent", () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "");

    renderWithQueryClient(<WorkspacePage />);

    expect(screen.getByText(/isn't configured/)).toBeInTheDocument();
  });

  it("lists datasets and shows the create-dataset form for signed-in users", async () => {
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_123");
    vi.mocked(useAuth).mockReturnValue({
      isSignedIn: true,
      getToken: vi.fn().mockResolvedValue("fake-token"),
    } as unknown as ReturnType<typeof useAuth>);
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
});
