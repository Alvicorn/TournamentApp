import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { ActivityEntry } from "./types";

type ActivityParams = {
  limit?: number;
  since?: string;
  division_id?: string;
  enabled?: boolean;
  refetchInterval?: number;
};

export function useActivity(tournamentId: string, params: ActivityParams = {}) {
  const { token } = useAuthStore();
  const { limit = 50, since, division_id, enabled = true, refetchInterval } = params;

  return useQuery<ActivityEntry[]>({
    queryKey: ["activity", tournamentId, { limit, since, division_id }],
    queryFn: () => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      if (since) qs.set("since", since);
      if (division_id) qs.set("division_id", division_id);
      return apiFetch<ActivityEntry[]>(
        `/api/v1/tournaments/${tournamentId}/activity?${qs}`,
        { token: token ?? "" }
      );
    },
    enabled: !!tournamentId && enabled,
    refetchInterval,
  });
}
