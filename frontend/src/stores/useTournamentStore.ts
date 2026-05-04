import { create } from "zustand";

export type LifecycleState = "setup" | "active" | "completed";

export type Tournament = {
  id: string;
  name: string;
  competition_date: string;
  time_zone: string;
  rounds_per_match: number;
  round_length_seconds: number;
  slideshow_slide_seconds: number;
  lifecycle_state: LifecycleState;
  is_demo: boolean;
  judge_auto_release_seconds: number;
};

type TournamentState = {
  tournament: Tournament | null;
  setTournament: (t: Tournament | null) => void;
};

export const useTournamentStore = create<TournamentState>()((set) => ({
  tournament: null,
  setTournament: (tournament) => set({ tournament }),
}));
