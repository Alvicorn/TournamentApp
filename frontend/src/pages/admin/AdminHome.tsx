import { Link } from "react-router-dom";
import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament, useTransitionLifecycle } from "../../api/tournaments";
import { useActivity } from "../../api/activity";

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

export default function AdminHome() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading } = useTournament();
  const { data: activity = [] } = useActivity(tournament?.id ?? "", {
    limit: 20,
    enabled: !!tournament?.id,
    refetchInterval: 5_000,
  });
  const transition = useTransitionLifecycle(tournament?.id ?? "");

  async function handleTransition(state: "active" | "completed") {
    try {
      await transition.mutateAsync(state);
      addToast(
        state === "active" ? "Tournament activated" : "Tournament completed",
        "success"
      );
    } catch {
      addToast("Failed to update tournament state", "error");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!tournament) {
    return (
      <div className="py-16 text-center">
        <p className="mb-4 text-slate-600">
          Get started by creating your first tournament.
        </p>
        <Link
          to="/admin/setup"
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900"
        >
          Create tournament
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tournament status card */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold text-slate-800">
              {tournament.name}
            </h1>
            <p className="text-sm text-slate-500">{tournament.competition_date}</p>
            <div className="flex gap-2">
              <StateBadge value={tournament.lifecycle_state} />
              {tournament.is_demo && <StateBadge value="demo" />}
            </div>
          </div>
          <div className="flex gap-2">
            {tournament.lifecycle_state === "setup" && (
              <button
                onClick={() => handleTransition("active")}
                disabled={transition.isPending}
                className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                Activate
              </button>
            )}
            {tournament.lifecycle_state === "active" && (
              <button
                onClick={() => handleTransition("completed")}
                disabled={transition.isPending}
                className="rounded bg-slate-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                Complete
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Activity feed */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="mb-4 font-semibold text-slate-800">Recent activity</h2>
        {activity.length === 0 ? (
          <p className="text-sm text-slate-400">No activity yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {activity.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-800">
                    <span className="font-medium">{entry.actor_display_name}</span>
                    {" — "}
                    {entry.description}
                  </p>
                  <p className="text-xs text-slate-400">{entry.action}</p>
                </div>
                <span className="shrink-0 text-xs text-slate-400">
                  {relativeTime(entry.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
