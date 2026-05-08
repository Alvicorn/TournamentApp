import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament } from "../../api/tournaments";
import { useBackups, useTriggerBackup } from "../../api/backups";

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AdminBackups() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading: tLoading } = useTournament();
  const { data: backups = [], isLoading: bLoading } = useBackups(
    tournament?.id ?? ""
  );
  const triggerBackup = useTriggerBackup(tournament?.id ?? "");

  async function handleSnapshot() {
    try {
      await triggerBackup.mutateAsync();
      addToast("Snapshot started", "success");
    } catch {
      addToast("Failed to start snapshot", "error");
    }
  }

  if (tLoading || bLoading) return <Skeleton className="h-64 w-full" />;

  if (!tournament) {
    return (
      <p className="text-slate-500">
        No active tournament. Create one in Setup first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Backups</h1>
        <button
          onClick={handleSnapshot}
          disabled={triggerBackup.isPending}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {triggerBackup.isPending ? "Snapshotting…" : "Snapshot Now"}
        </button>
      </div>

      {backups.length === 0 ? (
        <p className="text-sm text-slate-400">No backups yet.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Triggered by
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Description
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Started
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Size
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {backups.map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-2 text-slate-700">{b.triggered_by}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {b.pre_action_description ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(b.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {formatBytes(b.size_bytes)}
                  </td>
                  <td className="px-4 py-2">
                    <StateBadge value={b.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
