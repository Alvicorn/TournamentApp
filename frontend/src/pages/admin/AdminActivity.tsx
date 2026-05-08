import { useState } from "react";
import { Skeleton } from "../../components/Skeleton";
import { StateBadge } from "../../components/StateBadge";
import { useTournament } from "../../api/tournaments";
import { useDivisions } from "../../api/divisions";
import { useActivity } from "../../api/activity";
import type { ActorType } from "../../api/types";

const PAGE_SIZE = 50;

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

export default function AdminActivity() {
  const { data: tournament, isLoading: tLoading } = useTournament();
  const { data: divisions = [] } = useDivisions(tournament?.id ?? "");

  const [divisionId, setDivisionId] = useState("");
  const [actorType, setActorType] = useState<ActorType | "">("");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);

  const { data: entries = [], isLoading: aLoading } = useActivity(
    tournament?.id ?? "",
    {
      limit,
      division_id: divisionId || undefined,
      actor_type: actorType || undefined,
      enabled: !!tournament?.id,
      refetchInterval: 5_000,
    }
  );

  const filtered = entries.filter((e) => {
    if (search && !e.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (tLoading || aLoading) return <Skeleton className="h-64 w-full" />;

  if (!tournament) {
    return (
      <p className="text-slate-500">
        No active tournament. Create one in Setup first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-800">Activity log</h1>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3">
        <div>
          <label
            htmlFor="division-filter"
            className="mb-1 block text-xs font-medium text-slate-600"
          >
            Division
          </label>
          <select
            id="division-filter"
            aria-label="division"
            value={divisionId}
            onChange={(e) => setDivisionId(e.target.value)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">All divisions</option>
            {divisions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="actor-filter"
            className="mb-1 block text-xs font-medium text-slate-600"
          >
            Actor type
          </label>
          <select
            id="actor-filter"
            value={actorType}
            onChange={(e) => setActorType(e.target.value as ActorType | "")}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">All actors</option>
            <option value="admin">Admin</option>
            <option value="judge">Judge</option>
            <option value="system">System</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="search-filter"
            className="mb-1 block text-xs font-medium text-slate-600"
          >
            Search
          </label>
          <input
            id="search-filter"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search descriptions…"
            className="rounded border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-slate-400">
          No activity matches your filters.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Actor
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Action
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Description
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Type
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  When
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-2 font-medium text-slate-800">
                    {e.actor_display_name}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-500">
                    {e.action}
                  </td>
                  <td className="px-4 py-2 text-slate-700">{e.description}</td>
                  <td className="px-4 py-2">
                    <StateBadge value={e.actor_type} />
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {relativeTime(e.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {entries.length >= limit && (
        <button
          onClick={() => setLimit((prev) => prev + PAGE_SIZE)}
          className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          Load more
        </button>
      )}
    </div>
  );
}
