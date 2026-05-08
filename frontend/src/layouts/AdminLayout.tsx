import { Link, Outlet } from "react-router-dom";
import { ConnectionStatusIndicator } from "../components/ConnectionStatusIndicator";
import { RequireAuth } from "../components/RequireAuth";
import { Toaster } from "../components/Toaster";
import { useAuthStore } from "../stores/useAuthStore";

export function AdminLayout() {
  const { clearAuth } = useAuthStore();

  return (
    <RequireAuth role="admin" loginPath="/admin/login">
      <div className="hidden min-h-screen flex-col lg:flex">
        <nav className="flex shrink-0 items-center gap-6 border-b border-slate-200 bg-white px-6 py-3">
          <span className="font-semibold text-slate-800">Tournament Admin</span>
          <Link to="/admin" className="text-sm text-slate-600 hover:text-slate-900">
            Home
          </Link>
          <Link to="/admin/setup" className="text-sm text-slate-600 hover:text-slate-900">
            Setup
          </Link>
          <Link to="/admin/judges" className="text-sm text-slate-600 hover:text-slate-900">
            Judges
          </Link>
          <Link to="/admin/participants" className="text-sm text-slate-600 hover:text-slate-900">
            Participants
          </Link>
          <Link to="/admin/divisions" className="text-sm text-slate-600 hover:text-slate-900">
            Divisions
          </Link>
          <Link to="/admin/activity" className="text-sm text-slate-600 hover:text-slate-900">
            Activity
          </Link>
          <Link to="/admin/backups" className="text-sm text-slate-600 hover:text-slate-900">
            Backups
          </Link>
          <div className="ml-auto flex items-center gap-4">
            <ConnectionStatusIndicator />
            <button
              onClick={clearAuth}
              className="text-sm text-slate-600 hover:text-slate-900"
            >
              Log out
            </button>
          </div>
        </nav>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
        <Toaster />
      </div>
      <div className="flex min-h-screen items-center justify-center p-8 text-center text-slate-600 lg:hidden">
        Please use a desktop browser to access the admin panel.
      </div>
    </RequireAuth>
  );
}
