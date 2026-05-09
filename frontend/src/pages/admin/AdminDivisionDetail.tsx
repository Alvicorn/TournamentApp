import { FormEvent, useState } from "react";
import { useParams } from "react-router-dom";
import { Modal } from "../../components/Modal";
import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import { useTournament } from "../../api/tournaments";
import {
  useAssignParticipant,
  useDivisions,
  useGenerateRoundRobin,
  useMoveParticipant,
  useRemoveParticipantFromDivision,
  useUpdateDivision,
} from "../../api/divisions";
import { useParticipants } from "../../api/participants";
import { useEditResult, useMatches, useReorderMatches } from "../../api/matches";
import type { Match, MatchRound } from "../../api/types";

export default function AdminDivisionDetail() {
  const { id: divisionId = "" } = useParams<{ id: string }>();
  const { addToast } = useNotificationsStore();

  const { data: tournament } = useTournament();
  const tournamentId = tournament?.id ?? "";

  const { data: allDivisions = [], isLoading: dLoading } = useDivisions(tournamentId);
  const division = allDivisions.find((d) => d.id === divisionId);

  const { data: allParticipants = [], isLoading: pLoading } = useParticipants(tournamentId);
  const divisionParticipants = allParticipants.filter((p) => p.division_id === divisionId);
  const unassigned = allParticipants.filter((p) => !p.division_id && !p.is_withdrawn);

  const { data: matches = [], isLoading: mLoading } = useMatches(divisionId);

  const generateRR = useGenerateRoundRobin(tournamentId, divisionId);
  const assignParticipant = useAssignParticipant(tournamentId, divisionId);
  const moveParticipant = useMoveParticipant(tournamentId, divisionId);
  const updateDivision = useUpdateDivision(tournamentId);
  const reorderMatches = useReorderMatches(divisionId, tournamentId);
  const editResult = useEditResult(divisionId, tournamentId);
  const removeFromDivision = useRemoveParticipantFromDivision(tournamentId, divisionId);

  const [selectedAssign, setSelectedAssign] = useState("");
  const [editingMatch, setEditingMatch] = useState<Match | null>(null);
  const [roundScores, setRoundScores] = useState<MatchRound[]>([]);
  const [moveParticipantId, setMoveParticipantId] = useState<string | null>(null);
  const [moveTargetId, setMoveTargetId] = useState("");

  const isSetup = division?.state === "setup";
  const isRoundRobin = division?.state === "round_robin";
  const isPaused = division?.state === "paused";
  const canGenerate = isSetup;

  const sortedMatches = [...matches].sort((a, b) => a.order_index - b.order_index);

  async function handleGenerateRR() {
    try {
      await generateRR.mutateAsync();
      addToast("Round-robin generated", "success");
    } catch {
      addToast("Failed to generate round-robin", "error");
    }
  }

  async function handleAssign() {
    if (!selectedAssign) return;
    try {
      await assignParticipant.mutateAsync(selectedAssign);
      setSelectedAssign("");
      addToast("Participant assigned", "success");
    } catch {
      addToast("Failed to assign participant", "error");
    }
  }

  async function handleMove() {
    if (!moveParticipantId || !moveTargetId) return;
    try {
      await moveParticipant.mutateAsync({
        participantId: moveParticipantId,
        targetDivisionId: moveTargetId,
      });
      setMoveParticipantId(null);
      setMoveTargetId("");
      addToast("Participant moved", "success");
    } catch {
      addToast("Failed to move participant", "error");
    }
  }

  async function moveUp(index: number) {
    if (index === 0) return;
    const reordered = [...sortedMatches];
    [reordered[index - 1], reordered[index]] = [reordered[index], reordered[index - 1]];
    try {
      await reorderMatches.mutateAsync(reordered.map((m) => m.id));
    } catch {
      addToast("Failed to reorder matches", "error");
    }
  }

  async function moveDown(index: number) {
    if (index === sortedMatches.length - 1) return;
    const reordered = [...sortedMatches];
    [reordered[index], reordered[index + 1]] = [reordered[index + 1], reordered[index]];
    try {
      await reorderMatches.mutateAsync(reordered.map((m) => m.id));
    } catch {
      addToast("Failed to reorder matches", "error");
    }
  }

  function openEditResult(match: Match) {
    setEditingMatch(match);
    setRoundScores(
      match.rounds.length > 0
        ? match.rounds.map((r) => ({ ...r }))
        : Array.from({ length: tournament?.rounds_per_match ?? 3 }, (_, i) => ({
            round_number: i + 1,
            competitor_a_score: 0,
            competitor_b_score: 0,
          }))
    );
  }

  async function handleEditResult(e: FormEvent) {
    e.preventDefault();
    if (!editingMatch) return;
    try {
      await editResult.mutateAsync({
        matchId: editingMatch.id,
        roundScores,
      });
      setEditingMatch(null);
      addToast("Result updated", "success");
    } catch {
      addToast("Failed to update result", "error");
    }
  }

  async function togglePause() {
    if (!division) return;
    const newState = isPaused ? "round_robin" : "paused";
    try {
      await updateDivision.mutateAsync({
        id: divisionId,
        body: isPaused
          ? { state: newState }
          : { state: newState, paused_reason: "Paused by admin" },
      });
      addToast(isPaused ? "Division resumed" : "Division paused", "success");
    } catch {
      addToast("Failed to update division state", "error");
    }
  }

  if (dLoading || pLoading || mLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!division) {
    return <p className="text-slate-500">Division not found.</p>;
  }

  const nameMap = Object.fromEntries(allParticipants.map((p) => [p.id, p.name]));
  const otherDivisions = allDivisions.filter((d) => d.id !== divisionId);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-800">{division.name}</h1>
        <StateBadge value={division.state} />
      </div>

      {/* Participants panel */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="mb-3 font-semibold text-slate-700">Participants</h2>
        {divisionParticipants.length === 0 ? (
          <p className="text-sm text-slate-400">No participants assigned.</p>
        ) : (
          <ul className="mb-3 divide-y divide-slate-100">
            {divisionParticipants.map((p) => (
              <li key={p.id} className="flex items-center justify-between py-2">
                <span className="text-sm text-slate-800">{p.name}</span>
                {isSetup && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setMoveParticipantId(p.id)}
                      className="text-xs text-slate-500 hover:text-slate-700"
                    >
                      Move
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await removeFromDivision.mutateAsync(p.id);
                          addToast("Participant removed from division", "success");
                        } catch {
                          addToast("Failed to remove participant from division", "error");
                        }
                      }}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        {/* Assign dropdown */}
        {unassigned.length > 0 && (isSetup || isRoundRobin) && (
          <div className="flex gap-2">
            <select
              value={selectedAssign}
              onChange={(e) => setSelectedAssign(e.target.value)}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
            >
              <option value="">Select participant…</option>
              {unassigned.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleAssign}
              disabled={!selectedAssign || assignParticipant.isPending}
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Assign
            </button>
          </div>
        )}

        {/* Late addition label */}
        {isRoundRobin && (
          <p className="mt-2 text-xs text-slate-500">
            Use the Assign dropdown above to{" "}
            <span className="font-medium text-purple-700">Add Late Participant</span>.
          </p>
        )}
      </section>

      {/* Matches panel */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-700">Matches</h2>
          <button
            onClick={handleGenerateRR}
            disabled={!canGenerate || generateRR.isPending}
            className="rounded bg-purple-600 px-3 py-1.5 text-sm text-white hover:bg-purple-700 disabled:opacity-50"
            aria-label="Generate Round-Robin"
          >
            {generateRR.isPending ? "Generating…" : "Generate Round-Robin"}
          </button>
        </div>

        {sortedMatches.length === 0 ? (
          <p className="text-sm text-slate-400">No matches yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-600">#</th>
                <th className="px-3 py-2 text-left font-medium text-slate-600">Competitors</th>
                <th className="px-3 py-2 text-left font-medium text-slate-600">State</th>
                <th className="px-3 py-2 text-left font-medium text-slate-600">Winner</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedMatches.map((m, index) => (
                <tr key={m.id}>
                  <td className="px-3 py-2 text-slate-500">{index + 1}</td>
                  <td className="px-3 py-2 text-slate-800">
                    {nameMap[m.competitor_a_id] ?? m.competitor_a_id} vs{" "}
                    {nameMap[m.competitor_b_id] ?? m.competitor_b_id}
                  </td>
                  <td className="px-3 py-2">
                    <StateBadge value={m.state} />
                  </td>
                  <td className="px-3 py-2 text-slate-600">
                    {m.winner_id ? nameMap[m.winner_id] ?? m.winner_id : "—"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => moveUp(index)}
                        disabled={index === 0 || reorderMatches.isPending}
                        className="rounded border border-slate-200 px-1.5 py-0.5 text-xs hover:bg-slate-50 disabled:opacity-30"
                        title="Move up"
                      >
                        ↑
                      </button>
                      <button
                        onClick={() => moveDown(index)}
                        disabled={
                          index === sortedMatches.length - 1 ||
                          reorderMatches.isPending
                        }
                        className="rounded border border-slate-200 px-1.5 py-0.5 text-xs hover:bg-slate-50 disabled:opacity-30"
                        title="Move down"
                      >
                        ↓
                      </button>
                      {m.state === "submitted" && m.phase === "round_robin" && (
                        <button
                          onClick={() => openEditResult(m)}
                          className="ml-1 text-xs text-blue-600 hover:text-blue-800"
                          aria-label="Edit Result"
                        >
                          Edit Result
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Division controls */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="mb-3 font-semibold text-slate-700">Division controls</h2>
        <div className="flex items-center gap-4">
          <StateBadge value={division.state} />
          {(isRoundRobin || isPaused) && (
            <button
              onClick={togglePause}
              disabled={updateDivision.isPending}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {isPaused ? "Resume" : "Pause"}
            </button>
          )}
        </div>
        {division.paused_reason && isPaused && (
          <p className="mt-2 text-sm text-yellow-700">
            Paused: {division.paused_reason}
          </p>
        )}
      </section>

      {/* Edit result modal */}
      <Modal
        open={!!editingMatch}
        onClose={() => setEditingMatch(null)}
        title="Edit match result"
      >
        {editingMatch && (
          <form onSubmit={handleEditResult} className="space-y-3">
            <p className="text-sm text-slate-600">
              {nameMap[editingMatch.competitor_a_id] ?? "A"} vs{" "}
              {nameMap[editingMatch.competitor_b_id] ?? "B"}
            </p>
            {roundScores.map((r, i) => (
              <div key={r.round_number} className="flex items-center gap-3">
                <span className="w-16 text-sm text-slate-600">
                  Round {r.round_number}
                </span>
                <input
                  type="number"
                  min={0}
                  value={r.competitor_a_score}
                  onChange={(e) =>
                    setRoundScores((prev) =>
                      prev.map((s, j) =>
                        j === i
                          ? { ...s, competitor_a_score: Number(e.target.value) }
                          : s
                      )
                    )
                  }
                  className="w-16 rounded border border-slate-300 px-2 py-1 text-sm"
                  aria-label={`Round ${r.round_number} A score`}
                />
                <span className="text-slate-400">—</span>
                <input
                  type="number"
                  min={0}
                  value={r.competitor_b_score}
                  onChange={(e) =>
                    setRoundScores((prev) =>
                      prev.map((s, j) =>
                        j === i
                          ? { ...s, competitor_b_score: Number(e.target.value) }
                          : s
                      )
                    )
                  }
                  className="w-16 rounded border border-slate-300 px-2 py-1 text-sm"
                  aria-label={`Round ${r.round_number} B score`}
                />
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditingMatch(null)}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={editResult.isPending}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {editResult.isPending ? "Saving…" : "Save result"}
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* Move participant modal */}
      <Modal
        open={!!moveParticipantId}
        onClose={() => setMoveParticipantId(null)}
        title="Move participant"
      >
        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Target division
          </label>
          <select
            value={moveTargetId}
            onChange={(e) => setMoveTargetId(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Select division…</option>
            {otherDivisions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setMoveParticipantId(null)}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleMove}
              disabled={!moveTargetId || moveParticipant.isPending}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {moveParticipant.isPending ? "Moving…" : "Move"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
