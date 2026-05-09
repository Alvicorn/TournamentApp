import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { Division } from "./types";

export function useDivisions(tournamentId: string) {
  const { token } = useAuthStore();
  return useQuery<Division[]>({
    queryKey: ["divisions", tournamentId],
    queryFn: () =>
      apiFetch<Division[]>(
        `/api/v1/tournaments/${tournamentId}/divisions`,
        { token: token ?? "" }
      ),
    enabled: !!tournamentId,
  });
}

export function useCreateDivision(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string }) =>
      apiFetch<Division>(
        `/api/v1/tournaments/${tournamentId}/divisions`,
        { method: "POST", body, token: token ?? "" }
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] }),
  });
}

export function useUpdateDivision(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: { name?: string; state?: string; paused_reason?: string };
    }) =>
      apiFetch<Division>(`/api/v1/divisions/${id}`, {
        method: "PATCH",
        body,
        token: token ?? "",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] }),
  });
}

export function useDeleteDivision(tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (divisionId: string) =>
      apiFetch<void>(`/api/v1/divisions/${divisionId}`, {
        method: "DELETE",
        token: token ?? "",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] }),
  });
}

export function useAssignParticipant(tournamentId: string, divisionId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (participantId: string) =>
      apiFetch<void>(`/api/v1/divisions/${divisionId}/assign-participant`, {
        method: "POST",
        body: { participant_id: participantId },
        token: token ?? "",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] });
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] });
    },
  });
}

export function useMoveParticipant(tournamentId: string, divisionId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      participantId,
      targetDivisionId,
    }: {
      participantId: string;
      targetDivisionId: string;
    }) =>
      apiFetch<void>(`/api/v1/divisions/${divisionId}/move-participant`, {
        method: "POST",
        body: {
          participant_id: participantId,
          target_division_id: targetDivisionId,
        },
        token: token ?? "",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] });
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] });
    },
  });
}

export function useRemoveParticipantFromDivision(tournamentId: string, divisionId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (participantId: string) =>
      apiFetch<void>(`/api/v1/divisions/${divisionId}/remove-participant`, {
        method: "POST",
        body: { participant_id: participantId },
        token: token ?? "",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] });
      qc.invalidateQueries({ queryKey: ["participants", tournamentId] });
    },
  });
}


export function useGenerateRoundRobin(tournamentId: string, divisionId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<Division>(
        `/api/v1/divisions/${divisionId}/generate-round-robin`,
        { method: "POST", token: token ?? "" }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["divisions", tournamentId] });
      qc.invalidateQueries({ queryKey: ["matches", divisionId] });
    },
  });
}
