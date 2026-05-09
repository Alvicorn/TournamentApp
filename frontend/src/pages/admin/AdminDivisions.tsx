import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Modal } from "../../components/Modal";
import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament } from "../../api/tournaments";
import {
  useCreateDivision,
  useDeleteDivision,
  useDivisions,
  useUpdateDivision,
} from "../../api/divisions";
import type { Division } from "../../api/types";

export default function AdminDivisions() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading: tLoading } = useTournament();
  const { data: divisions = [], isLoading: dLoading } = useDivisions(
    tournament?.id ?? ""
  );
  const createDivision = useCreateDivision(tournament?.id ?? "");
  const updateDivision = useUpdateDivision(tournament?.id ?? "");
  const deleteDivision = useDeleteDivision(tournament?.id ?? "");

  const [newName, setNewName] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameName, setRenameName] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Division | null>(null);
  const [pausingId, setPausingId] = useState<string | null>(null);
  const [pauseReason, setPauseReason] = useState("");

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    try {
      await createDivision.mutateAsync({ name: newName.trim() });
      setNewName("");
      setShowAddForm(false);
      addToast("Division created", "success");
    } catch {
      addToast("Failed to create division", "error");
    }
  }

  async function handleRename(e: FormEvent) {
    e.preventDefault();
    if (!renamingId) return;
    try {
      await updateDivision.mutateAsync({
        id: renamingId,
        body: { name: renameName.trim() },
      });
      setRenamingId(null);
      addToast("Division renamed", "success");
    } catch {
      addToast("Failed to rename division", "error");
    }
  }

  async function handlePause(div: Division) {
    const isPaused = div.state === "paused";
    try {
      await updateDivision.mutateAsync({
        id: div.id,
        body: isPaused
          ? { state: "round_robin" }
          : { state: "paused", paused_reason: pauseReason || "Paused by admin" },
      });
      setPausingId(null);
      setPauseReason("");
      addToast(isPaused ? "Division resumed" : "Division paused", "success");
    } catch {
      addToast("Failed to update division state", "error");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await deleteDivision.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
      addToast("Division deleted", "success");
    } catch {
      addToast("Failed to delete division", "error");
    }
  }

  if (tLoading || dLoading) return <Skeleton className="h-64 w-full" />;

  if (!tournament) {
    return (
      <p className="text-slate-500">No active tournament. Create one in Setup first.</p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Divisions</h1>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900"
        >
          New Division
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleCreate}
          className="flex gap-2 rounded border border-slate-200 bg-white p-3"
        >
          <input
            required
            placeholder="Division name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={createDivision.isPending}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createDivision.isPending ? "Creating…" : "Create"}
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

      {divisions.length === 0 ? (
        <p className="text-sm text-slate-400">No divisions yet.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {divisions.map((div) => (
            <div
              key={div.id}
              className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4"
            >
              {renamingId === div.id ? (
                <form onSubmit={handleRename} className="flex gap-2">
                  <input
                    value={renameName}
                    onChange={(e) => setRenameName(e.target.value)}
                    className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
                  />
                  <button
                    type="submit"
                    className="rounded bg-blue-600 px-2 py-1 text-xs text-white"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setRenamingId(null)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs"
                  >
                    Cancel
                  </button>
                </form>
              ) : (
                <div className="flex items-start justify-between">
                  <h2 className="font-medium text-slate-800">{div.name}</h2>
                  <StateBadge value={div.state} />
                </div>
              )}
              {div.paused_reason && div.state === "paused" && (
                <p className="text-xs text-yellow-700">
                  Paused: {div.paused_reason}
                </p>
              )}
              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <Link
                  to={`/admin/divisions/${div.id}`}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  View
                </Link>
                <button
                  onClick={() => {
                    setRenamingId(div.id);
                    setRenameName(div.name);
                  }}
                  className="text-xs text-slate-500 hover:text-slate-700"
                >
                  Rename
                </button>
                <button
                  onClick={() => {
                    if (div.state === "paused") {
                      handlePause(div);
                    } else {
                      setPausingId(div.id);
                    }
                  }}
                  className="text-xs text-slate-500 hover:text-slate-700"
                >
                  {div.state === "paused" ? "Resume" : "Pause"}
                </button>
                <button
                  onClick={() => setPendingDelete(div)}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pause reason modal */}
      <Modal
        open={!!pausingId}
        onClose={() => setPausingId(null)}
        title="Pause division"
      >
        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Reason (optional)
          </label>
          <input
            value={pauseReason}
            onChange={(e) => setPauseReason(e.target.value)}
            placeholder="e.g. waiting for judges"
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setPausingId(null)}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                const div = divisions.find((d) => d.id === pausingId);
                if (div) handlePause(div);
              }}
              className="rounded bg-yellow-500 px-3 py-1.5 text-sm text-white hover:bg-yellow-600"
            >
              Pause
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete modal */}
      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Delete division?"
      >
        <p className="mb-4 text-sm text-slate-700">
          Delete <strong>{pendingDelete?.name}</strong>? This cannot be undone.
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
            disabled={deleteDivision.isPending}
            className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
          >
            {deleteDivision.isPending ? "Deleting…" : "Delete"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
