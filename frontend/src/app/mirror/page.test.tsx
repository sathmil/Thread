import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";

vi.mock("@/lib/api", () => ({
  mirrorStory: vi.fn(),
}));

import { mirrorStory } from "@/lib/api";

import MirrorPage from "./page";

describe("MirrorPage", () => {
  it("shows matches and the fingerprint source after submitting a pasted story", async () => {
    vi.mocked(mirrorStory).mockResolvedValue({
      matches: [
        {
          story_id: "002",
          title: "Every morning, my school bus drives past the reservation sign.",
          preview: "Every morning, my school bus drives past the reservation sign...",
          score: 0.72,
          theme: "Education & Access",
          explanation: "Both stories score high on belonging and identity.",
        },
      ],
      fingerprint: { hope: 0.2, isolation: 0.1, identity: 0.3, family: 0.4, growth: 0.1, grief: 0.0, belonging: 0.5, agency: 0.2 },
      fingerprint_source: "rule_based",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<MirrorPage />);

    const textarea = screen.getByPlaceholderText(/write a few sentences/i);
    await user.type(textarea, "I moved every year and never felt like I belonged.");
    await user.click(screen.getByRole("button", { name: /find my matches/i }));

    await waitFor(() =>
      expect(mirrorStory).toHaveBeenCalledWith("I moved every year and never felt like I belonged.")
    );

    expect(await screen.findByText(/You're closest to 1 story about Education & Access/)).toBeInTheDocument();
    expect(screen.getByText("Every morning, my school bus drives past the reservation sign.")).toBeInTheDocument();
    expect(screen.getByText("0.72 similarity")).toBeInTheDocument();
    expect(screen.getByText(/keyword heuristic/)).toBeInTheDocument();
  });

  it("disables the submit button until text is entered", () => {
    renderWithQueryClient(<MirrorPage />);

    expect(screen.getByRole("button", { name: /find my matches/i })).toBeDisabled();
  });
});
