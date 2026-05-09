import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { CustomFieldSpec, LifecycleState, Tournament } from "./types";

export function useTournament() {
  const { token } = useAuthStore();
  return useQuery<Tournament | null>({
    queryKey: ["tournament"],
    queryFn: async () => {
      try {
        return await apiFetch<Tournament>("/api/v1/tournaments/active", {
          token: token ?? "",
        });
      } catch (e) {
        const err = e as { name?: string; status?: number };
        if ((e instanceof ApiError || err.name === "ApiError") && err.status === 404) return null;
        throw e;
      }
    },
  });
}

export type TournamentPayload = {
  name: string;
  competition_date: string;
  time_zone: string;
  rounds_per_match: number;
  round_length_seconds: number;
  slideshow_slide_seconds: number;
  is_demo: boolean;
  judge_auto_release_seconds: number;
  custom_participant_fields: CustomFieldSpec[];
};

export function useCreateTournament() {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TournamentPayload) =>
      apiFetch<Tournament>("/api/v1/tournaments", {
        method: "POST",
        body,
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament"] }),
  });
}

export function useUpdateTournament(id: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<TournamentPayload>) =>
      apiFetch<Tournament>(`/api/v1/tournaments/${id}`, {
        method: "PATCH",
        body,
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament"] }),
  });
}

export function useTransitionLifecycle(id: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (state: LifecycleState) =>
      apiFetch<Tournament>(`/api/v1/tournaments/${id}/lifecycle`, {
        method: "POST",
        body: { state },
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament"] }),
  });
}

export function useResetTournament(id: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<Tournament>(`/api/v1/tournaments/${id}/reset`, {
        method: "POST",
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament"] }),
  });
}
