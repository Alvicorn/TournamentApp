import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useNotificationsStore } from "../stores/useNotificationsStore";
import { Toaster } from "../components/Toaster";
import { Modal } from "../components/Modal";

beforeEach(() => {
  useNotificationsStore.setState({ toasts: [] });
});

describe("Toaster", () => {
  it("renders a toast message from the store", () => {
    useNotificationsStore.setState({
      toasts: [{ id: "1", message: "Saved!", variant: "success" }],
    });
    render(<Toaster />);
    expect(screen.getByText("Saved!")).toBeInTheDocument();
  });

  it("renders nothing when no toasts", () => {
    const { container } = render(<Toaster />);
    expect(container.firstChild).toBeNull();
  });
});

describe("Modal", () => {
  it("renders children when open", () => {
    render(
      <Modal open={true} onClose={() => {}} title="Test modal">
        <p>Modal body</p>
      </Modal>
    );
    expect(screen.getByText("Modal body")).toBeInTheDocument();
    expect(screen.getByText("Test modal")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <Modal open={false} onClose={() => {}} title="Test modal">
        <p>Modal body</p>
      </Modal>
    );
    expect(container.firstChild).toBeNull();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose} title="Test">
        <p>body</p>
      </Modal>
    );
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
