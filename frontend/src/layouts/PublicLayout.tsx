import { Outlet } from "react-router-dom";
import { ConnectionStatusIndicator } from "../components/ConnectionStatusIndicator";

export function PublicLayout() {
  return (
    <div className="min-h-screen">
      <ConnectionStatusIndicator />
      <Outlet />
    </div>
  );
}
