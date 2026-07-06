import { create } from 'zustand';
import { ID } from '@/models';

interface ChatState {
  activeConversationId: ID | null;
  setActiveConversationId: (id: ID | null) => void;
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  messageInput: string;
  setMessageInput: (input: string) => void;
  drafts: Record<ID, string>;
  saveDraft: (conversationId: ID, draft: string) => void;
  getDraft: (conversationId: ID) => string | undefined;
  clearDraft: (conversationId: ID) => void;
  isLoadingMessages: boolean;
  setIsLoadingMessages: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),

  isStreaming: false,
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),

  messageInput: '',
  setMessageInput: (input) => set({ messageInput: input }),

  drafts: {},
  saveDraft: (conversationId, draft) =>
    set((state) => ({
      drafts: { ...state.drafts, [conversationId]: draft },
    })),
  getDraft: (conversationId) => get().drafts[conversationId],
  clearDraft: (conversationId) =>
    set((state) => {
      const { [conversationId]: _, ...rest } = state.drafts;
      return { drafts: rest };
    }),

  isLoadingMessages: false,
  setIsLoadingMessages: (loading) => set({ isLoadingMessages: loading }),

  error: null,
  setError: (error) => set({ error }),
}));
