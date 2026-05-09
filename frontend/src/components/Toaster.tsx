import { useCallback, useEffect, useRef } from "react";
import { useNotificationsStore } from "../stores/useNotificationsStore";

const VARIANT_CLASSES: Record<string, string> = {
  info: "bg-blue-600",
  success: "bg-green-600",
  warning: "bg-yellow-500",
  error: "bg-red-600",
};

const TIMEOUT_MS = 5000;

function Toast({ t, onDismiss }: { t: { id: string; message: string; variant: string }; onDismiss: (id: string) => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const start = useCallback(() => {
    timerRef.current = setTimeout(() => onDismiss(t.id), TIMEOUT_MS);
  }, [onDismiss, t.id]);

  const pause = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  useEffect(() => {
    start();
    return () => pause();
  }, [start]);

  return (
    <div
      key={t.id}
      role="alert"
      onMouseEnter={pause}
      onMouseLeave={start}
      className={`flex items-center gap-3 rounded px-4 py-3 text-sm text-white shadow-lg ${VARIANT_CLASSES[t.variant]}`}
    >
      <span>{t.message}</span>
      <button
        onClick={() => onDismiss(t.id)}
        className="ml-2 font-bold opacity-75 hover:opacity-100"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export function Toaster() {
  const { toasts, dismissToast } = useNotificationsStore();
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <Toast key={t.id} t={t} onDismiss={dismissToast} />
      ))}
    </div>
  );
}
