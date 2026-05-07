import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { Judge } from "./types";

export function useJudges(tournamentId: string) {
  const { token } = useAuthStore();
  return useQuery<Judge[]>({
    queryKey: ["judges", tournamentId],
    queryFn: () =>
      apiFetch<Judge[]>(`/api/v1/tournaments/${tournamentId}/judges`, {
        token: token ?? "",
      }),
    enabled: !!tournamentId,
  });
}

export function useAddJudge(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string }) =>
      apiFetch<Judge>(`/api/v1/tournaments/${tournamentId}/judges`, {
        method: "POST",
        body,
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["judges", tournamentId] }),
  });
}

export function useDeleteJudge(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (judgeId: string) =>
      apiFetch<void>(`/api/v1/judges/${judgeId}`, {
        method: "DELETE",
        token: token ?? "",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["judges", tournamentId] }),
  });
}
