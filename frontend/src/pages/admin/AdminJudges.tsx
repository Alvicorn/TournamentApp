import { FormEvent, useState } from "react";
import { Modal } from "../../components/Modal";
import { Skeleton } from "../../components/Skeleton";
import { format_judge_code } from "../../lib/judgeCode";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament } from "../../api/tournaments";
import { useAddJudge, useDeleteJudge, useJudges } from "../../api/judges";
import type { Judge } from "../../api/types";

export default function AdminJudges() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading: tLoading } = useTournament();
  const { data: judges = [], isLoading: jLoading } = useJudges(
    tournament?.id ?? ""
  );
  const addJudge = useAddJudge(tournament?.id ?? "");
  const deleteJudge = useDeleteJudge(tournament?.id ?? "");

  const [newName, setNewName] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Judge | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await addJudge.mutateAsync({ name: newName.trim() });
      setNewName("");
      setShowAddForm(false);
      addToast("Judge added", "success");
    } catch {
      addToast("Failed to add judge", "error");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await deleteJudge.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
      addToast("Judge removed", "success");
    } catch {
      addToast("Failed to remove judge", "error");
    }
  }

  async function copyCode(code: string) {
    await navigator.clipboard.writeText(format_judge_code(code));
    setCopied(code);
    setTimeout(() => setCopied(null), 2000);
  }

  if (tLoading || jLoading) return <Skeleton className="h-64 w-full" />;

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
        <h1 className="text-xl font-semibold text-slate-800">Judges</h1>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900"
        >
          Add Judge
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleAdd}
          className="flex gap-2 rounded border border-slate-200 bg-white p-3"
        >
          <input
            required
            placeholder="Judge name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={addJudge.isPending}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {addJudge.isPending ? "Adding…" : "Add"}
          </button>
          <button
            type="button"
            onClick={() => setShowAddForm(false)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
        </form>
      )}

      {judges.length === 0 ? (
        <p className="text-sm text-slate-400">
          No judges yet. Add your first judge above.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Name
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Code
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Added
                </th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {judges.map((j) => (
                <tr key={j.id}>
                  <td className="px-4 py-2 font-medium text-slate-800">
                    {j.name}
                  </td>
                  <td className="px-4 py-2">
                    <span className="font-mono text-slate-700">
                      {format_judge_code(j.code)}
                    </span>
                    <button
                      onClick={() => copyCode(j.code)}
                      className="ml-2 text-xs text-slate-400 hover:text-slate-600"
                      title="Copy code"
                    >
                      {copied === j.code ? "✓" : "⎘"}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(j.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => setPendingDelete(j)}
                      className="text-xs text-red-500 hover:text-red-700"
                      aria-label="Delete judge"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Confirm deletion"
      >
        <p className="mb-2 text-sm text-slate-700">
          Remove <strong>{pendingDelete?.name}</strong> from the tournament?
        </p>
        <p className="mb-4 text-sm text-slate-500">
          If this judge has an active match, it will be paused.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={() => setPendingDelete(null)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={deleteJudge.isPending}
            className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
          >
            {deleteJudge.isPending ? "Removing…" : "Remove"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
