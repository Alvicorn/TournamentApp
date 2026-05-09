import { ChangeEvent, FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { is_valid_judge_code, format_judge_code } from "../../lib/judgeCode";
import { apiFetch } from "../../api/client";
import { useAuthStore } from "../../stores/useAuthStore";

type LoginResponse = { access_token: string; judge_id: string; tournament_id: string };

export default function JudgeLogin() {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setJudge } = useAuthStore();
  const navigate = useNavigate();

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.toUpperCase().replace(/[^23456789ABCDEFGHJKMNPQRSTUVWXYZ-]/g, "");
    setCode(format_judge_code(raw));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const stripped = code.replace("-", "");
    if (!is_valid_judge_code(stripped)) {
      setError("Code not recognized. Check with the tournament admin.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<LoginResponse>("/api/v1/auth/judge/login", {
        method: "POST",
        body: { code: stripped },
      });
      setJudge(data.access_token, data.judge_id, data.tournament_id);
      navigate("/judge");
    } catch {
      setError("Code not recognized.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-xs space-y-4">
        <h1 className="text-xl font-semibold text-slate-800">Judge login</h1>
        <p className="text-sm text-slate-500">Get your 8-character code from the tournament admin.</p>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Judge code
          </label>
          <input
            type="text"
            required
            maxLength={9}
            value={code}
            onChange={handleChange}
            placeholder="ABCD-EFGH1"
            className="w-full rounded border border-slate-300 px-3 py-2 font-mono text-lg tracking-widest uppercase focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-slate-800 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {loading ? "Logging in…" : "Log in"}
        </button>
      </form>
    </div>
  );
}
