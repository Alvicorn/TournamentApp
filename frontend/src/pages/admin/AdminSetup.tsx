import { FormEvent, useEffect, useState } from "react";
import { Skeleton } from "../../components/Skeleton";
import { useNotificationsStore } from "../../stores/useNotificationsStore";
import {
  useCreateTournament,
  useTournament,
  useUpdateTournament,
  type TournamentPayload,
} from "../../api/tournaments";
import type { CustomFieldSpec } from "../../api/types";

type FieldRow = CustomFieldSpec & { _id: string };

function makeEmptyField(): FieldRow {
  return { key: "", label: "", type: "text", required: false, _id: crypto.randomUUID() };
}

export default function AdminSetup() {
  const { addToast } = useNotificationsStore();
  const { data: tournament, isLoading } = useTournament();

  const [name, setName] = useState("");
  const [competitionDate, setCompetitionDate] = useState("");
  const [roundsPerMatch, setRoundsPerMatch] = useState(3);
  const [roundLengthSeconds, setRoundLengthSeconds] = useState(120);
  const [slideshowSlideSeconds, setSlideshowSlideSeconds] = useState(10);
  const [isDemo, setIsDemo] = useState(false);
  const [judgeAutoReleaseSeconds, setJudgeAutoReleaseSeconds] = useState(300);
  const [customFields, setCustomFields] = useState<FieldRow[]>([]);

  useEffect(() => {
    if (tournament) {
      setName(tournament.name);
      setCompetitionDate(tournament.competition_date);
      setRoundsPerMatch(tournament.rounds_per_match);
      setRoundLengthSeconds(tournament.round_length_seconds);
      setSlideshowSlideSeconds(tournament.slideshow_slide_seconds);
      setIsDemo(tournament.is_demo);
      setJudgeAutoReleaseSeconds(tournament.judge_auto_release_seconds);
      setCustomFields(tournament.custom_participant_fields.map((f) => ({ ...f, _id: crypto.randomUUID() })));
    }
  }, [tournament]);

  const create = useCreateTournament();
  const update = useUpdateTournament(tournament?.id ?? "");
  const isPending = create.isPending || update.isPending;
  const fieldsLocked =
    tournament?.lifecycle_state === "active" ||
    tournament?.lifecycle_state === "completed";
  const isCompleted = tournament?.lifecycle_state === "completed";

  function addField() {
    setCustomFields((prev) => [...prev, makeEmptyField()]);
  }

  function removeField(index: number) {
    setCustomFields((prev) => prev.filter((_, i) => i !== index));
  }

  function updateField(index: number, patch: Partial<CustomFieldSpec>) {
    setCustomFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, ...patch } : f))
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const payload: TournamentPayload = {
      name,
      competition_date: competitionDate,
      time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      rounds_per_match: roundsPerMatch,
      round_length_seconds: roundLengthSeconds,
      slideshow_slide_seconds: slideshowSlideSeconds,
      is_demo: isDemo,
      judge_auto_release_seconds: judgeAutoReleaseSeconds,
      custom_participant_fields: customFields.map(({ _id: _, ...rest }) => rest),
    };
    try {
      if (tournament) {
        await update.mutateAsync(payload);
        addToast("Tournament updated", "success");
      } else {
        await create.mutateAsync(payload);
        addToast("Tournament created", "success");
      }
    } catch {
      addToast("Failed to save tournament", "error");
    }
  }

  if (isLoading) return <Skeleton className="h-96 w-full" />;

  const inputCls =
    "w-full rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50";

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">
        {tournament ? "Edit tournament" : "Create tournament"}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Name
          </label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isCompleted}
            className={inputCls}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Competition date
          </label>
          <input
            type="date"
            required
            value={competitionDate}
            onChange={(e) => setCompetitionDate(e.target.value)}
            disabled={isCompleted}
            className={inputCls}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Rounds per match
            </label>
            <input
              type="number"
              min={1}
              required
              value={roundsPerMatch}
              onChange={(e) => setRoundsPerMatch(Number(e.target.value))}
              disabled={isCompleted}
              className={inputCls}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Round length (seconds)
            </label>
            <input
              type="number"
              min={1}
              required
              value={roundLengthSeconds}
              onChange={(e) => setRoundLengthSeconds(Number(e.target.value))}
              disabled={isCompleted}
              className={inputCls}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Slideshow slide (seconds)
            </label>
            <input
              type="number"
              min={1}
              required
              value={slideshowSlideSeconds}
              onChange={(e) => setSlideshowSlideSeconds(Number(e.target.value))}
              disabled={isCompleted}
              className={inputCls}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Judge auto-release (seconds)
            </label>
            <input
              type="number"
              min={0}
              required
              value={judgeAutoReleaseSeconds}
              onChange={(e) =>
                setJudgeAutoReleaseSeconds(Number(e.target.value))
              }
              disabled={isCompleted}
              className={inputCls}
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            id="is_demo"
            type="checkbox"
            checked={isDemo}
            onChange={(e) => setIsDemo(e.target.checked)}
            disabled={isCompleted}
            className="rounded border-slate-300"
          />
          <label htmlFor="is_demo" className="text-sm font-medium text-slate-700">
            Demo mode
          </label>
        </div>

        {/* Custom field builder */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">
              Custom participant fields
            </span>
            {!fieldsLocked && (
              <button
                type="button"
                onClick={addField}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Add Field
              </button>
            )}
          </div>
          {customFields.length === 0 && (
            <p className="text-sm text-slate-400">No custom fields defined.</p>
          )}
          <div className="space-y-2">
            {customFields.map((f, i) => (
              <div
                key={f._id}
                className="flex items-center gap-2 rounded border border-slate-200 p-2"
              >
                <input
                  aria-label="key"
                  placeholder="key"
                  value={f.key}
                  onChange={(e) => updateField(i, { key: e.target.value })}
                  disabled={fieldsLocked}
                  className="w-24 rounded border border-slate-300 px-2 py-1 text-xs disabled:bg-slate-50"
                />
                <input
                  aria-label="label"
                  placeholder="label"
                  value={f.label}
                  onChange={(e) => updateField(i, { label: e.target.value })}
                  disabled={fieldsLocked}
                  className="flex-1 rounded border border-slate-300 px-2 py-1 text-xs disabled:bg-slate-50"
                />
                <select
                  value={f.type}
                  onChange={(e) =>
                    updateField(i, {
                      type: e.target.value as CustomFieldSpec["type"],
                    })
                  }
                  disabled={fieldsLocked}
                  className="rounded border border-slate-300 px-2 py-1 text-xs disabled:bg-slate-50"
                >
                  <option value="text">text</option>
                  <option value="number">number</option>
                  <option value="select">select</option>
                </select>
                <label className="flex items-center gap-1 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={f.required}
                    onChange={(e) =>
                      updateField(i, { required: e.target.checked })
                    }
                    disabled={fieldsLocked}
                  />
                  req
                </label>
                {!fieldsLocked && (
                  <button
                    type="button"
                    onClick={() => removeField(i)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {!isCompleted && (
          <button
            type="submit"
            disabled={isPending}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
          >
            {isPending
              ? "Saving…"
              : tournament
                ? "Save changes"
                : "Create tournament"}
          </button>
        )}
      </form>
    </div>
  );
}
