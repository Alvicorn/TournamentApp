import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { makeQueryClient } from "./helpers";
import AdminDivisionDetail from "../pages/admin/AdminDivisionDetail";
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

const DIVISION_SETUP = {
  id: "div-1",
  tournament_id: "t1",
  name: "Heavyweight",
  state: "setup",
  paused_reason: null,
};

const DIVISION_RR = { ...DIVISION_SETUP, state: "round_robin" };

function renderDetail(
  divisionState: "setup" | "round_robin" = "setup",
  extraMatches: unknown[] = []
) {
  const division = divisionState === "setup" ? DIVISION_SETUP : DIVISION_RR;
  vi.mocked(client.apiFetch).mockImplementation((path: string) => {
    if (path.includes("/tournaments/active")) return Promise.resolve(TOURNAMENT);
    if (path.includes("/divisions/div-1/matches") || (path.includes("/divisions/") && path.includes("/matches"))) return Promise.resolve(extraMatches);
    if (path.includes("/divisions")) return Promise.resolve([division]);
    if (path.includes("/participants")) return Promise.resolve([]);
    return Promise.reject(new Error(`Unmocked: ${path}`));
  });
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/admin/divisions/div-1"]}>
        <Routes>
          <Route path="/admin/divisions/:id" element={<AdminDivisionDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useAuthStore.setState({
    token: "test-token",
    role: "admin",
    userId: "uid",
    tournamentId: null,
  });
  vi.clearAllMocks();
});

describe("AdminDivisionDetail", () => {
  it("shows Generate Round-Robin button disabled when not in setup state", async () => {
    renderDetail("round_robin");
    const btn = await screen.findByRole("button", { name: /generate round-robin/i });
    expect(btn).toBeDisabled();
  });

  it("shows Generate Round-Robin button enabled when division is in setup", async () => {
    renderDetail("setup");
    const btn = await screen.findByRole("button", { name: /generate round-robin/i });
    expect(btn).not.toBeDisabled();
  });

  it("hides Add Late Participant UI in setup state", async () => {
    renderDetail("setup");
    await screen.findByRole("button", { name: /generate round-robin/i });
    expect(screen.queryByText(/add late participant/i)).toBeNull();
  });

  it("shows Add Late Participant UI in round_robin state", async () => {
    renderDetail("round_robin");
    await screen.findByText(/add late participant/i);
  });

  it("shows Edit Result button for submitted round_robin match", async () => {
    const match = {
      id: "m1",
      division_id: "div-1",
      phase: "round_robin",
      state: "submitted",
      order_index: 0,
      competitor_a_id: "p1",
      competitor_b_id: "p2",
      winner_id: "p1",
      assigned_judge_id: null,
      rounds: [{ round_number: 1, competitor_a_score: 10, competitor_b_score: 8 }],
    };
    renderDetail("round_robin", [match]);
    await screen.findByRole("button", { name: /edit result/i });
  });
});
