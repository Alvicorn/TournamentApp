import { create } from "zustand";
import { persist } from "zustand/middleware";

type SubscriptionsState = {
  deviceId: string;
  subscribedParticipantIds: string[];
  subscribe: (participantId: string) => void;
  unsubscribe: (participantId: string) => void;
};

function generateDeviceId(): string {
  return crypto.randomUUID();
}

export const useSubscriptionsStore = create<SubscriptionsState>()(
  persist(
    (set) => ({
      deviceId: generateDeviceId(),
      subscribedParticipantIds: [],

      subscribe: (participantId) =>
        set((s) => ({
          subscribedParticipantIds: s.subscribedParticipantIds.includes(participantId)
            ? s.subscribedParticipantIds
            : [...s.subscribedParticipantIds, participantId],
        })),

      unsubscribe: (participantId) =>
        set((s) => ({
          subscribedParticipantIds: s.subscribedParticipantIds.filter((id) => id !== participantId),
        })),
    }),
    { name: "tournament-subscriptions" }
  )
);
