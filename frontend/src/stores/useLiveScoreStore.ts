import { create } from "zustand";

export type LiveScore = {
  matchId: string;
  competitorAScore: number;
  competitorBScore: number;
  currentRound: number;
  matchState: string;
  isSuddenDeath: boolean;
};

type LiveScoreState = {
  scores: Record<string, LiveScore>;
  upsertScore: (score: LiveScore) => void;
  clearMatch: (matchId: string) => void;
  clearAll: () => void;
};

export const useLiveScoreStore = create<LiveScoreState>()((set) => ({
  scores: {},

  upsertScore: (score) =>
    set((s) => ({ scores: { ...s.scores, [score.matchId]: score } })),

  clearMatch: (matchId) =>
    set((s) => {
      const scores = { ...s.scores };
      delete scores[matchId];
      return { scores };
    }),

  clearAll: () => set({ scores: {} }),
}));
