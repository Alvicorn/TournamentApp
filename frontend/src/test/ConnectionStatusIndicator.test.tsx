import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { ConnectionStatusIndicator } from "../components/ConnectionStatusIndicator";
import { useUIStore } from "../stores/useUIStore";

beforeEach(() => {
  useUIStore.setState({ connectionStatus: "live", lastSuccessfulPollAt: null });
});

describe("ConnectionStatusIndicator", () => {
  it("shows Live when connected", () => {
    render(<ConnectionStatusIndicator />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("shows Reconnecting when store says so", () => {
    useUIStore.setState({ connectionStatus: "reconnecting" });
    render(<ConnectionStatusIndicator />);
    expect(screen.getByText("Reconnecting")).toBeInTheDocument();
  });

  it("shows Disconnected when store says so", () => {
    useUIStore.setState({ connectionStatus: "disconnected" });
    render(<ConnectionStatusIndicator />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });
});
