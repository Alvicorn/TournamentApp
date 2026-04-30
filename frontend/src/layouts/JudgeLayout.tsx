import { Outlet } from "react-router-dom";
import { ConnectionStatusIndicator } from "../components/ConnectionStatusIndicator";
import { RequireAuth } from "../components/RequireAuth";
import { useAuthStore } from "../stores/useAuthStore";

export function JudgeLayout() {
  const { clearAuth } = useAuthStore();

  return (
    <RequireAuth role="judge" loginPath="/judge/login">
      <div className="min-h-screen">
        <nav className="border-b border-slate-200 bg-white px-4 py-3 flex items-center justify-between">
          <span className="font-semibold text-slate-800">Judge</span>
          <div className="flex items-center gap-3">
            <ConnectionStatusIndicator />
            <button
              onClick={clearAuth}
              className="text-sm text-slate-600 hover:text-slate-900"
            >
              Log out
            </button>
          </div>
        </nav>
        <main>
          <Outlet />
        </main>
      </div>
    </RequireAuth>
  );
}
