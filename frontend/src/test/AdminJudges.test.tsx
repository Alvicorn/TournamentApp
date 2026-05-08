import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithClient } from "./helpers";
import AdminJudges from "../pages/admin/AdminJudges";
import * as client from "../api/client";
import { useAuthStore } from "../stores/useAuthStore";

vi.mock("../api/client", () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      public detail: string
    ) {
      super(detail);
      this.name = "ApiError";
    }
  }
  return { apiFetch: vi.fn(), ApiError };
});

const TOURNAMENT = {
  id: "t1",
  name: "Test Tournament",
  competition_date: "2026-06-01",
  time_zone: "UTC",
  rounds_per_match: 3,
  round_length_seconds: 120,
  slideshow_slide_seconds: 10,
  is_demo: false,
  judge_auto_release_seconds: 300,
  lifecycle_state: "setup",
  custom_participant_fields: [],
};

const JUDGE = {
  id: "j1",
  tournament_id: "t1",
  name: "Alice",
  code: "ABCD1234",
  created_at: "2026-05-01T00:00:00Z",
};

function setupMocks() {
  vi.mocked(client.apiFetch).mockImplementation((path: string) => {
    if (path.includes("/tournaments/active")) return Promise.resolve(TOURNAMENT);
    if (path.includes("/judges")) return Promise.resolve([JUDGE]);
    return Promise.reject(new Error(`Unmocked: ${path}`));
  });
}

beforeEach(() => {
  useAuthStore.setState({
    token: "test-token",
    role: "admin",
    userId: "uid",
    tournamentId: null,
  });
  vi.clearAllMocks();
  setupMocks();
});

describe("AdminJudges", () => {
  it("displays judge code formatted as XXXX-XXXX", async () => {
    renderWithClient(<AdminJudges />);
    await screen.findByText("Alice");
    expect(screen.getByText("ABCD-1234")).toBeInTheDocument();
  });

  it("opens a delete confirmation modal when delete is clicked", async () => {
    renderWithClient(<AdminJudges />);
    await screen.findByText("Alice");
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/confirm/i)).toBeInTheDocument();
  });
});
