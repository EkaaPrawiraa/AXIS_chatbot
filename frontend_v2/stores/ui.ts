import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ThemeMode } from '@/lib/config/theme';
import { LOCAL_STORAGE_KEYS } from '@/lib/constants';

interface UIState {
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  mobileNavOpen: boolean;
  setMobileNavOpen: (open: boolean) => void;
  activeModal: string | null;
  setActiveModal: (modal: string | null) => void;
  toasts: Array<{ id: string; type: 'success' | 'error' | 'info'; message: string }>;
  addToast: (message: string, type: 'success' | 'error' | 'info') => void;
  removeToast: (id: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      themeMode: 'system',
      setThemeMode: (mode) => set({ themeMode: mode }),

      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      mobileNavOpen: false,
      setMobileNavOpen: (open) => set({ mobileNavOpen: open }),

      activeModal: null,
      setActiveModal: (modal) => set({ activeModal: modal }),

      toasts: [],
      addToast: (message, type) =>
        set((state) => ({
          toasts: [
            ...state.toasts,
            { id: Date.now().toString(), type, message },
          ],
        })),
      removeToast: (id) =>
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        })),
    }),
    {
      name: LOCAL_STORAGE_KEYS.THEME_MODE,
      partialize: (state) => ({ themeMode: state.themeMode, sidebarCollapsed: state.sidebarCollapsed }),
    }
  )
);
