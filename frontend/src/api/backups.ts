import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { Backup } from "./types";

export function useBackups(tournamentId: string) {
  const { token } = useAuthStore();
  return useQuery<Backup[]>({
    queryKey: ["backups", tournamentId],
    queryFn: () =>
      apiFetch<Backup[]>(
        `/api/v1/tournaments/${tournamentId}/backups`,
        { token: token ?? "" }
      ),
    enabled: !!tournamentId,
  });
}

export function useTriggerBackup(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<Backup>(`/api/v1/tournaments/${tournamentId}/backups`, {
        method: "POST",
        token: token ?? "",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["backups", tournamentId] }),
  });
}
