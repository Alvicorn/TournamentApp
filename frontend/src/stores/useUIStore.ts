import { create } from "zustand";

export type ConnectionStatus = "live" | "reconnecting" | "disconnected";

type UIState = {
  slideshowIndex: number;
  connectionStatus: ConnectionStatus;
  lastSuccessfulPollAt: number | null;
  setSlideshowIndex: (i: number) => void;
  setConnectionStatus: (s: ConnectionStatus) => void;
  recordSuccessfulPoll: () => void;
};

export const useUIStore = create<UIState>()((set) => ({
  slideshowIndex: 0,
  connectionStatus: "live",
  lastSuccessfulPollAt: null,

  setSlideshowIndex: (slideshowIndex) => set({ slideshowIndex }),

  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  recordSuccessfulPoll: () =>
    set({ lastSuccessfulPollAt: Date.now(), connectionStatus: "live" }),
}));
