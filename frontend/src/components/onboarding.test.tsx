import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { Onboarding } from "./onboarding";

describe("Onboarding", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("shows the welcome modal on a first visit", async () => {
    render(<Onboarding />);

    expect(await screen.findByText("Find yourself in someone else's experience")).toBeInTheDocument();
  });

  it("dismisses and remembers the visit when 'Start exploring' is clicked", async () => {
    const user = userEvent.setup();
    render(<Onboarding />);

    await screen.findByText("Find yourself in someone else's experience");
    await user.click(screen.getByRole("button", { name: "Start exploring" }));

    await waitFor(() =>
      expect(screen.queryByText("Find yourself in someone else's experience")).not.toBeInTheDocument()
    );
    expect(window.localStorage.getItem("thread_onboarding_seen")).toBe("1");
  });

  it("does not reappear on a later visit", () => {
    window.localStorage.setItem("thread_onboarding_seen", "1");
    render(<Onboarding />);

    expect(screen.queryByText("Find yourself in someone else's experience")).not.toBeInTheDocument();
  });
});
