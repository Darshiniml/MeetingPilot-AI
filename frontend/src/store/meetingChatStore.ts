import { create } from "zustand";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  status?: "pending" | "error";
};

type MeetingChatState = {
  selectedMeetingId: number | null;
  conversations: Record<number, ChatMessage[]>;
  recentMeetingIds: number[];
  selectMeeting: (meetingId: number) => void;
  addMessage: (meetingId: number, message: ChatMessage) => void;
  updateMessage: (meetingId: number, messageId: string, update: Partial<ChatMessage>) => void;
  clearConversation: (meetingId: number) => void;
};

const storageKey = "meetingpilot-meeting-chat";

const loadStoredState = (): Pick<MeetingChatState, "conversations" | "recentMeetingIds"> => {
  try {
    return JSON.parse(localStorage.getItem(storageKey) ?? "{}") as Pick<MeetingChatState, "conversations" | "recentMeetingIds">;
  } catch {
    return { conversations: {}, recentMeetingIds: [] };
  }
};

const persist = (conversations: Record<number, ChatMessage[]>, recentMeetingIds: number[]) => {
  localStorage.setItem(storageKey, JSON.stringify({ conversations, recentMeetingIds }));
};

const stored = loadStoredState();

export const useMeetingChatStore = create<MeetingChatState>((set) => ({
  selectedMeetingId: null,
  conversations: stored.conversations ?? {},
  recentMeetingIds: stored.recentMeetingIds ?? [],
  selectMeeting: (meetingId) => set((state) => {
    const recentMeetingIds = [meetingId, ...state.recentMeetingIds.filter((id) => id !== meetingId)].slice(0, 6);
    persist(state.conversations, recentMeetingIds);
    return { selectedMeetingId: meetingId, recentMeetingIds };
  }),
  addMessage: (meetingId, message) => set((state) => {
    const conversations = { ...state.conversations, [meetingId]: [...(state.conversations[meetingId] ?? []), message] };
    persist(conversations, state.recentMeetingIds);
    return { conversations };
  }),
  updateMessage: (meetingId, messageId, update) => set((state) => {
    const conversations = { ...state.conversations, [meetingId]: (state.conversations[meetingId] ?? []).map((message) => message.id === messageId ? { ...message, ...update } : message) };
    persist(conversations, state.recentMeetingIds);
    return { conversations };
  }),
  clearConversation: (meetingId) => set((state) => {
    const conversations = { ...state.conversations, [meetingId]: [] };
    persist(conversations, state.recentMeetingIds);
    return { conversations };
  }),
}));
