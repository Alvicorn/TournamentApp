const COLOR_MAP: Record<string, string> = {
  setup: "bg-slate-100 text-slate-700",
  active: "bg-green-100 text-green-800",
  completed: "bg-blue-100 text-blue-700",
  round_robin: "bg-purple-100 text-purple-800",
  play_ins: "bg-indigo-100 text-indigo-800",
  semis: "bg-indigo-100 text-indigo-800",
  finals: "bg-indigo-100 text-indigo-800",
  paused: "bg-yellow-100 text-yellow-800",
  scheduled: "bg-slate-100 text-slate-700",
  in_progress: "bg-green-100 text-green-800",
  submitted: "bg-blue-100 text-blue-700",
  pending_review: "bg-yellow-100 text-yellow-800",
  pending: "bg-yellow-100 text-yellow-800",
  complete: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  demo: "bg-orange-100 text-orange-800",
};

type Props = { value: string };

export function StateBadge({ value }: Props) {
  const cls = COLOR_MAP[value] ?? "bg-slate-100 text-slate-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {value}
    </span>
  );
}
