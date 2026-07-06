import { create } from 'zustand';
import { ID } from '@/models';

interface SessionState {
  userId: ID | null;
  setUserId: (id: ID | null) => void;
  isAuthenticated: boolean;
  setIsAuthenticated: (authenticated: boolean) => void;
  isConnected: boolean;
  setIsConnected: (connected: boolean) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  isInitialized: boolean;
  setIsInitialized: (initialized: boolean) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  userId: null,
  setUserId: (id) => set({ userId: id }),

  isAuthenticated: false,
  setIsAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),

  isConnected: false,
  setIsConnected: (connected) => set({ isConnected: connected }),

  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  error: null,
  setError: (error) => set({ error }),

  isInitialized: false,
  setIsInitialized: (initialized) => set({ isInitialized: initialized }),
}));
