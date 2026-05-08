import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithClient } from "./helpers";
import AdminActivity from "../pages/admin/AdminActivity";
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
  name: "Test",
  competition_date: "2026-06-01",
  time_zone: "UTC",
  rounds_per_match: 3,
  round_length_seconds: 120,
  slideshow_slide_seconds: 10,
  is_demo: false,
  judge_auto_release_seconds: 300,
  lifecycle_state: "active",
  custom_participant_fields: [],
};

const DIVISIONS = [
  {
    id: "div-1",
    tournament_id: "t1",
    name: "Heavyweight",
    state: "round_robin",
    paused_reason: null,
  },
  {
    id: "div-2",
    tournament_id: "t1",
    name: "Lightweight",
    state: "setup",
    paused_reason: null,
  },
];

const ENTRY_GLOBAL = {
  id: "e1",
  tournament_id: "t1",
  actor_type: "admin",
  actor_id: "u1",
  actor_display_name: "admin@test.com",
  action: "tournament.activated",
  description: "Tournament activated",
  division_id: null,
  created_at: new Date().toISOString(),
};

const ENTRY_DIV1 = {
  id: "e2",
  tournament_id: "t1",
  actor_type: "admin",
  actor_id: "u1",
  actor_display_name: "admin@test.com",
  action: "division.round_robin_generated",
  description: "Round-robin generated for Heavyweight",
  division_id: "div-1",
  created_at: new Date().toISOString(),
};

beforeEach(() => {
  useAuthStore.setState({
    token: "test-token",
    role: "admin",
    userId: "uid",
    tournamentId: null,
  });
  vi.clearAllMocks();
});

describe("AdminActivity", () => {
  it("renders activity entries", async () => {
    vi.mocked(client.apiFetch).mockImplementation((path: string) => {
      if (path.includes("/tournaments/active")) return Promise.resolve(TOURNAMENT);
      if (path.includes("/divisions")) return Promise.resolve(DIVISIONS);
      if (path.includes("/activity")) return Promise.resolve([ENTRY_GLOBAL, ENTRY_DIV1]);
      return Promise.reject(new Error(`Unmocked: ${path}`));
    });
    renderWithClient(<AdminActivity />);
    await screen.findByText("Tournament activated");
    expect(
      screen.getByText("Round-robin generated for Heavyweight")
    ).toBeInTheDocument();
  });

  it("filters by division_id when a division is selected", async () => {
    vi.mocked(client.apiFetch).mockImplementation((path: string) => {
      if (path.includes("/tournaments/active")) return Promise.resolve(TOURNAMENT);
      if (path.includes("/divisions")) return Promise.resolve(DIVISIONS);
      // When division_id filter is applied, return only div-1 entry
      if (path.includes("division_id=div-1"))
        return Promise.resolve([ENTRY_DIV1]);
      // Default activity (no filter) returns both
      if (path.includes("/activity")) return Promise.resolve([ENTRY_GLOBAL, ENTRY_DIV1]);
      return Promise.reject(new Error(`Unmocked: ${path}`));
    });
    renderWithClient(<AdminActivity />);
    await screen.findByText("Tournament activated");

    // Select "Heavyweight" division from the combobox
    const select = screen.getByRole("combobox", { name: /division/i });
    fireEvent.change(select, { target: { value: "div-1" } });

    await screen.findByText("Round-robin generated for Heavyweight");
    expect(screen.queryByText("Tournament activated")).toBeNull();
  });
});
