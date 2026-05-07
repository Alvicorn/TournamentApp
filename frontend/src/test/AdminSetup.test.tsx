import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithClient } from "./helpers";
import AdminSetup from "../pages/admin/AdminSetup";
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

beforeEach(() => {
  useAuthStore.setState({
    token: "test-token",
    role: "admin",
    userId: "uid",
    tournamentId: null,
  });
  vi.clearAllMocks();
  // Re-apply mock after clearAllMocks
  vi.mocked(client.apiFetch).mockRejectedValue(
    Object.assign(new Error("not found"), { status: 404, name: "ApiError" })
  );
});

describe("AdminSetup — custom field builder", () => {
  it("adds a custom field row when Add Field is clicked", async () => {
    renderWithClient(<AdminSetup />);
    const btn = await screen.findByText("Add Field");
    fireEvent.click(btn);
    expect(screen.getAllByLabelText("key")).toHaveLength(1);
  });

  it("removes a custom field row when Remove is clicked", async () => {
    renderWithClient(<AdminSetup />);
    const addBtn = await screen.findByText("Add Field");
    fireEvent.click(addBtn);
    fireEvent.click(addBtn);
    expect(screen.getAllByLabelText("key")).toHaveLength(2);
    const removeBtns = screen.getAllByText("Remove");
    fireEvent.click(removeBtns[0]);
    expect(screen.getAllByLabelText("key")).toHaveLength(1);
  });

  it("disables custom field inputs when tournament is active", async () => {
    vi.mocked(client.apiFetch).mockImplementation((path: string) => {
      if (path.includes("/tournaments/active")) {
        return Promise.resolve({
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
          custom_participant_fields: [
            { key: "weight", label: "Weight", type: "number", required: false },
          ],
        });
      }
      return Promise.reject(new Error(`Unmocked: ${path}`));
    });
    renderWithClient(<AdminSetup />);
    await screen.findByDisplayValue("weight");
    expect(screen.getByDisplayValue("weight")).toBeDisabled();
    expect(screen.queryByText("Add Field")).toBeNull();
  });
});
