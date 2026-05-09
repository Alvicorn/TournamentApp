import { FormEvent, useState } from "react";
import { Modal } from "../../components/Modal";
import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament } from "../../api/tournaments";
import { useDivisions } from "../../api/divisions";
import {
  useAddParticipant,
  useDeleteParticipant,
  useParticipants,
  useUpdateParticipant,
} from "../../api/participants";
import type { CustomFieldSpec, Participant } from "../../api/types";

function buildEmptyFields(
  specs: CustomFieldSpec[]
): Record<string, string | number | null> {
  return Object.fromEntries(specs.map((s) => [s.key, null]));
}

export default function AdminParticipants() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading: tLoading } = useTournament();
  const { data: participants = [], isLoading: pLoading } = useParticipants(
    tournament?.id ?? ""
  );
  const { data: divisions = [] } = useDivisions(tournament?.id ?? "");
  const addParticipant = useAddParticipant(tournament?.id ?? "");
  const updateParticipant = useUpdateParticipant(tournament?.id ?? "");
  const deleteParticipant = useDeleteParticipant(tournament?.id ?? "");

  const specs: CustomFieldSpec[] = tournament?.custom_participant_fields ?? [];

  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCustom, setNewCustom] = useState<Record<string, string | number | null>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editCustom, setEditCustom] = useState<Record<string, string | number | null>>({});
  const [pendingDelete, setPendingDelete] = useState<Participant | null>(null);

  function startEdit(p: Participant) {
    setEditingId(p.id);
    setEditName(p.name);
    setEditCustom({ ...p.custom_fields });
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    try {
      await addParticipant.mutateAsync({
        name: newName.trim(),
        custom_fields: newCustom,
      });
      setNewName("");
      setNewCustom(buildEmptyFields(specs));
      setShowAddForm(false);
      addToast("Participant added", "success");
    } catch {
      addToast("Failed to add participant", "error");
    }
  }

  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    if (!editingId) return;
    try {
      await updateParticipant.mutateAsync({
        id: editingId,
        body: { name: editName.trim(), custom_fields: editCustom },
      });
      setEditingId(null);
      addToast("Participant updated", "success");
    } catch {
      addToast("Failed to update participant", "error");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await deleteParticipant.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
      addToast("Participant removed", "success");
    } catch {
      addToast("Failed to remove participant", "error");
    }
  }

  const divisionNameMap = Object.fromEntries(divisions.map((d) => [d.id, d.name]));

  if (tLoading || pLoading) return <Skeleton className="h-64 w-full" />;

  if (!tournament) {
    return (
      <p className="text-slate-500">No active tournament. Create one in Setup first.</p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Participants</h1>
        <button
          onClick={() => {
            setShowAddForm((v) => !v);
            setNewCustom(buildEmptyFields(specs));
          }}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900"
        >
          Add Participant
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleAdd}
          className="flex flex-wrap gap-2 rounded border border-slate-200 bg-white p-3"
        >
          <input
            required
            placeholder="Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {specs.map((s) => (
            <input
              key={s.key}
              placeholder={s.label}
              required={s.required}
              type={s.type === "number" ? "number" : "text"}
              value={String(newCustom[s.key] ?? "")}
              onChange={(e) =>
                setNewCustom((prev) => ({
                  ...prev,
                  [s.key]:
                    s.type === "number"
                      ? Number(e.target.value)
                      : e.target.value,
                }))
              }
              className="rounded border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          ))}
          <button
            type="submit"
            disabled={addParticipant.isPending}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {addParticipant.isPending ? "Adding…" : "Add"}
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

      {participants.length === 0 ? (
        <p className="text-sm text-slate-400">No participants yet.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-600">Name</th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">Division</th>
                {specs.map((s) => (
                  <th key={s.key} className="px-4 py-2 text-left font-medium text-slate-600">
                    {s.label}
                  </th>
                ))}
                <th className="px-4 py-2 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {participants.map((p) =>
                editingId === p.id ? (
                  <tr key={p.id}>
                    <td className="px-4 py-2" colSpan={specs.length + 3}>
                      <form onSubmit={handleUpdate} className="flex flex-wrap gap-2">
                        <input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="rounded border border-slate-300 px-2 py-1 text-xs"
                        />
                        {specs.map((s) => (
                          <input
                            key={s.key}
                            placeholder={s.label}
                            type={s.type === "number" ? "number" : "text"}
                            value={String(editCustom[s.key] ?? "")}
                            onChange={(e) =>
                              setEditCustom((prev) => ({
                                ...prev,
                                [s.key]:
                                  s.type === "number"
                                    ? Number(e.target.value)
                                    : e.target.value,
                              }))
                            }
                            className="rounded border border-slate-300 px-2 py-1 text-xs"
                          />
                        ))}
                        <button
                          type="submit"
                          disabled={updateParticipant.isPending}
                          className="rounded bg-blue-600 px-2 py-1 text-xs text-white"
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="rounded border border-slate-300 px-2 py-1 text-xs"
                        >
                          Cancel
                        </button>
                      </form>
                    </td>
                  </tr>
                ) : (
                  <tr key={p.id}>
                    <td className="px-4 py-2 font-medium text-slate-800">{p.name}</td>
                    <td className="px-4 py-2">
                      {p.division_id
                        ? <span className="text-slate-500">{divisionNameMap[p.division_id] ?? p.division_id}</span>
                        : <span className="text-xs italic text-slate-400">Unassigned</span>}
                    </td>
                    {specs.map((s) => (
                      <td key={s.key} className="px-4 py-2 text-slate-600">
                        {p.custom_fields[s.key] ?? "—"}
                      </td>
                    ))}
                    <td className="px-4 py-2">
                      {p.is_withdrawn ? (
                        <StateBadge value="withdrawn" />
                      ) : (
                        <span className="text-xs text-slate-400">active</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => startEdit(p)}
                        className="mr-2 text-xs text-blue-600 hover:text-blue-800"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setPendingDelete(p)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Remove participant?"
      >
        <p className="mb-2 text-sm text-slate-700">
          Remove <strong>{pendingDelete?.name}</strong>?
        </p>
        <p className="mb-4 text-sm text-slate-500">
          If this participant has matches, they will be marked as withdrawn instead of deleted.
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
            disabled={deleteParticipant.isPending}
            className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
          >
            {deleteParticipant.isPending ? "Removing…" : "Remove"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
