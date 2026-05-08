import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { Match, MatchRound } from "./types";

export function useMatches(divisionId: string) {
  const { token } = useAuthStore();
  return useQuery<Match[]>({
    queryKey: ["matches", divisionId],
    queryFn: () =>
      apiFetch<Match[]>(`/api/v1/divisions/${divisionId}/matches`, {
        token: token ?? "",
      }),
    enabled: !!divisionId,
  });
}

export function useReorderMatches(divisionId: string, tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderedMatchIds: string[]) =>
      apiFetch<void>(`/api/v1/divisions/${divisionId}/reorder-matches`, {
        method: "POST",
        body: { ordered_match_ids: orderedMatchIds },
        token: token ?? "",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matches", divisionId] });
      qc.invalidateQueries({ queryKey: ["activity", tournamentId] });
    },
  });
}

export function useEditResult(divisionId: string, tournamentId: string) {
  const { token } = useAuthStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      matchId,
      roundScores,
    }: {
      matchId: string;
      roundScores: MatchRound[];
    }) =>
      apiFetch<Match>(`/api/v1/matches/${matchId}/edit-result`, {
        method: "POST",
        body: { round_scores: roundScores },
        token: token ?? "",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matches", divisionId] });
      qc.invalidateQueries({ queryKey: ["activity", tournamentId] });
    },
  });
}
