import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <p className="text-slate-600">We couldn&apos;t find what you were looking for.</p>
      <Link to="/" className="text-sm text-blue-600 underline">
        Return to dashboard
      </Link>
    </div>
  );
}
