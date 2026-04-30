import { useEffect } from "react";
import { useUIStore } from "../stores/useUIStore";

const STATUS_LABELS = {
  live: "Live",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
} as const;

const STATUS_COLORS = {
  live: "bg-green-500",
  reconnecting: "bg-yellow-400",
  disconnected: "bg-red-500",
} as const;

export function ConnectionStatusIndicator() {
  const { connectionStatus, lastSuccessfulPollAt, setConnectionStatus } = useUIStore();

  // Promote live → reconnecting → disconnected based on time since last poll.
  useEffect(() => {
    if (connectionStatus === "live" && lastSuccessfulPollAt === null) return;

    const interval = setInterval(() => {
      if (lastSuccessfulPollAt === null) return;
      const elapsed = Date.now() - lastSuccessfulPollAt;
      if (elapsed > 30_000) {
        setConnectionStatus("disconnected");
      } else if (elapsed > 5_000) {
        setConnectionStatus("reconnecting");
      }
    }, 1_000);

    return () => clearInterval(interval);
  }, [connectionStatus, lastSuccessfulPollAt, setConnectionStatus]);

  return (
    <div
      className="flex items-center gap-1.5 text-xs font-medium text-slate-600"
      aria-label={`Connection status: ${STATUS_LABELS[connectionStatus]}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${STATUS_COLORS[connectionStatus]}`}
        aria-hidden
      />
      {STATUS_LABELS[connectionStatus]}
    </div>
  );
}
