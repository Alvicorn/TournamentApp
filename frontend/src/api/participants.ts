import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { Participant } from "./types";

export function useParticipants(tournamentId: string) {
  const { token } = useAuthStore();
  return useQuery<Participant[]>({
    queryKey: ["participants", tournamentId],
    queryFn: () =>
      apiFetch<Participant[]>(
        `/api/v1/tournaments/${tournamentId}/participants`,
        { token: token ?? "" }
      ),
    enabled: !!tournamentId,
  });
}

export function useAddParticipant(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      custom_fields: Record<string, string | number | null>;
    }) =>
      apiFetch<Participant>(
        `/api/v1/tournaments/${tournamentId}/participants`,
        { method: "POST", body, token: token ?? "" }
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] }),
  });
}

export function useUpdateParticipant(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: {
        name?: string;
        custom_fields?: Record<string, string | number | null>;
        division_id?: null;
      };
    }) =>
      apiFetch<Participant>(`/api/v1/participants/${id}`, {
        method: "PATCH",
        body,
        token: token ?? "",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] }),
  });
}

export function useDeleteParticipant(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (participantId: string) =>
      apiFetch<void>(`/api/v1/participants/${participantId}`, {
        method: "DELETE",
        token: token ?? "",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] }),
  });
}
