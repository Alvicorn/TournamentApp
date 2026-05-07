import { useNotificationsStore } from "../stores/useNotificationsStore";

const VARIANT_CLASSES: Record<string, string> = {
  info: "bg-blue-600",
  success: "bg-green-600",
  warning: "bg-yellow-500",
  error: "bg-red-600",
};

export function Toaster() {
  const { toasts, dismissToast } = useNotificationsStore();
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={`flex items-center gap-3 rounded px-4 py-3 text-sm text-white shadow-lg ${VARIANT_CLASSES[t.variant]}`}
        >
          <span>{t.message}</span>
          <button
            onClick={() => dismissToast(t.id)}
            className="ml-2 font-bold opacity-75 hover:opacity-100"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
