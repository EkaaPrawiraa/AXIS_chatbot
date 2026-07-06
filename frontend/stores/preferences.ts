import { create } from 'zustand';
import type { ChatResponseMode } from '@/models';

export type AppLanguage = 'id' | 'en';

const LANGUAGE_STORAGE_KEY = 'companion:language';
const CHAT_RESPONSE_MODE_STORAGE_KEY = 'companion:chat-response-mode';

interface PreferencesState {
  language: AppLanguage;
  chatResponseMode: ChatResponseMode;
  setLanguage: (language: AppLanguage) => void;
  setChatResponseMode: (mode: ChatResponseMode) => void;
  hydrateLanguage: () => void;
  hydrateChatResponseMode: () => void;
}

const getStoredLanguage = (): AppLanguage => {
  if (typeof window === 'undefined') return 'id';
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  const language = stored === 'en' || stored === 'id' ? stored : 'id';
  document.documentElement.lang = language;
  return language;
};

const getStoredChatResponseMode = (): ChatResponseMode => {
  if (typeof window === 'undefined') return 'normal';
  const stored = window.localStorage.getItem(CHAT_RESPONSE_MODE_STORAGE_KEY);
  return stored === 'stream' ? 'stream' : 'normal';
};

export const usePreferencesStore = create<PreferencesState>((set) => ({
  language: 'id',
  chatResponseMode: 'normal',
  setLanguage: (language) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
      document.documentElement.lang = language;
    }
    set({ language });
  },
  setChatResponseMode: (mode) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(CHAT_RESPONSE_MODE_STORAGE_KEY, mode);
    }
    set({ chatResponseMode: mode });
  },
  hydrateLanguage: () => {
    set({ language: getStoredLanguage() });
  },
  hydrateChatResponseMode: () => {
    set({ chatResponseMode: getStoredChatResponseMode() });
  },
}));
