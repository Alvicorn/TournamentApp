import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useAuthStore } from "../stores/useAuthStore";
import type { ActivityEntry } from "./types";

type ActivityParams = {
  limit?: number;
  since?: string;
  division_id?: string;
  actor_type?: string;
  enabled?: boolean;
  refetchInterval?: number;
};

export function useActivity(tournamentId: string, params: ActivityParams = {}) {
  const { token } = useAuthStore();
  const { limit = 50, since, division_id, actor_type, enabled = true, refetchInterval } = params;

  return useQuery<ActivityEntry[]>({
    queryKey: ["activity", tournamentId, { limit, since, division_id, actor_type }],
    queryFn: () => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      if (since) qs.set("since", since);
      if (division_id) qs.set("division_id", division_id);
      if (actor_type) qs.set("actor_type", actor_type);
      return apiFetch<ActivityEntry[]>(
        `/api/v1/tournaments/${tournamentId}/activity?${qs}`,
        { token: token ?? "" }
      );
    },
    enabled: !!tournamentId && enabled,
    refetchInterval,
  });
}
