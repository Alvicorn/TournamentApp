import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role = "admin" | "judge" | "public";

type AuthState = {
  role: Role;
  token: string | null;
  userId: string | null;
  tournamentId: string | null;
  setAdmin: (token: string, userId: string) => void;
  setJudge: (token: string, judgeId: string, tournamentId: string) => void;
  clearAuth: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      role: "public",
      token: null,
      userId: null,
      tournamentId: null,

      setAdmin: (token, userId) =>
        set({ role: "admin", token, userId, tournamentId: null }),

      setJudge: (token, judgeId, tournamentId) =>
        set({ role: "judge", token, userId: judgeId, tournamentId }),

      clearAuth: () =>
        set({ role: "public", token: null, userId: null, tournamentId: null }),
    }),
    { name: "tournament-auth" }
  )
);
