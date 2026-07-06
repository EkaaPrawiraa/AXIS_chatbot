import { create } from 'zustand';
import { AuthResponse, AuthUser, ID, UserProfile } from '@/models';
import { authAPI } from '@/lib/api/auth';

const SESSION_STORAGE_KEY = 'companion:session';

interface SessionState {
  userId: ID | null;
  token: string | null;
  user: AuthUser | null;
  profile: UserProfile | null;
  setUserId: (id: ID | null) => void;
  setSession: (session: AuthResponse) => void;
  initializeSession: () => void;
  clearSession: () => void;
  setProfile: (profile: UserProfile | null) => void;
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
  token: null,
  user: null,
  profile: null,
  setUserId: (id) => set({ userId: id }),
  setProfile: (profile) =>
    set((state) => {
      const nextUser =
        profile && state.user
          ? {
              ...state.user,
              displayName: profile.name || state.user.displayName,
              preferredLanguage: profile.language || state.user.preferredLanguage,
              preferredVoiceId: profile.preferredVoiceId || state.user.preferredVoiceId,
              preferredTtsModel: profile.preferredTtsModel || state.user.preferredTtsModel,
              preferredResponseModel: profile.preferredResponseModel || state.user.preferredResponseModel,
              gender: profile.gender || state.user.gender,
              safetyTermsAccepted: Boolean(profile.safetyTermsAccepted),
              safetyTermsVersion: profile.safetyTermsVersion || state.user.safetyTermsVersion,
              safetyTermsAcceptedAt: profile.safetyTermsAcceptedAt || state.user.safetyTermsAcceptedAt,
            }
          : state.user;
      return { profile, user: nextUser };
    }),
  setSession: (session) => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth-token');
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
    set({
      userId: session.user.id,
      token: null,
      user: session.user,
      profile: session.profile,
      isAuthenticated: true,
      isInitialized: true,
      error: null,
    });
  },
  initializeSession: async () => {
    if (typeof window === 'undefined') {
      set({ isInitialized: true });
      return;
    }

    localStorage.removeItem('auth-token');
    localStorage.removeItem(SESSION_STORAGE_KEY);
    if (!hasCookie('axis_csrf')) {
      set({
        userId: null,
        token: null,
        user: null,
        profile: null,
        isAuthenticated: false,
        isInitialized: true,
        error: null,
      });
      return;
    }

    try {
      const session = await authAPI.session();
      set({
        userId: session.user.id,
        token: null,
        user: session.user,
        profile: session.profile,
        isAuthenticated: true,
        isInitialized: true,
        error: null,
      });
    } catch {
      set({
        userId: null,
        token: null,
        user: null,
        profile: null,
        isAuthenticated: false,
        isInitialized: true,
      });
    }
  },
  clearSession: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth-token');
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
    set({
      userId: null,
      token: null,
      user: null,
      profile: null,
      isAuthenticated: false,
      error: null,
    });
  },

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

function hasCookie(name: string): boolean {
  if (typeof document === 'undefined') return false;
  const prefix = `${name}=`;
  return document.cookie.split('; ').some((part) => part.startsWith(prefix));
}
