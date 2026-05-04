import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../stores/useAuthStore";
import { useAuthStore } from "../stores/useAuthStore";

type Props = {
  role: Role;
  loginPath: string;
  children: React.ReactNode;
};

export function RequireAuth({ role, loginPath, children }: Props) {
  const currentRole = useAuthStore((s) => s.role);
  const location = useLocation();

  if (currentRole !== role) {
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
