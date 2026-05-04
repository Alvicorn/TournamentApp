import { create } from "zustand";

export type Toast = {
  id: string;
  message: string;
  variant: "info" | "warning" | "error" | "success";
};

type NotificationsState = {
  toasts: Toast[];
  addToast: (message: string, variant?: Toast["variant"]) => void;
  dismissToast: (id: string) => void;
};

export const useNotificationsStore = create<NotificationsState>()((set) => ({
  toasts: [],

  addToast: (message, variant = "info") =>
    set((s) => ({
      toasts: [...s.toasts, { id: crypto.randomUUID(), message, variant }],
    })),

  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
