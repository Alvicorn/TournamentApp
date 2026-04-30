import { Outlet } from "react-router-dom";
import { ConnectionStatusIndicator } from "../components/ConnectionStatusIndicator";
import { RequireAuth } from "../components/RequireAuth";
import { useAuthStore } from "../stores/useAuthStore";

export function AdminLayout() {
  const { clearAuth } = useAuthStore();

  return (
    <RequireAuth role="admin" loginPath="/admin/login">
      <div className="min-h-screen hidden lg:block">
        <nav className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
          <span className="font-semibold text-slate-800">Tournament Admin</span>
          <div className="flex items-center gap-4">
            <ConnectionStatusIndicator />
            <button
              onClick={clearAuth}
              className="text-sm text-slate-600 hover:text-slate-900"
            >
              Log out
            </button>
          </div>
        </nav>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <div className="lg:hidden flex items-center justify-center min-h-screen p-8 text-center text-slate-600">
        Please use a desktop browser to access the admin panel.
      </div>
    </RequireAuth>
  );
}
