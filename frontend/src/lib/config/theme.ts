export const THEME_CONFIG = {
  light: {
    background: '#ffffff',
    foreground: '#0d0d0d',
    card: '#f7f7f8',
    cardForeground: '#0d0d0d',
    primary: '#0d0d0d',
    primaryForeground: '#ffffff',
    secondary: '#e5e5ea',
    secondaryForeground: '#0d0d0d',
    accent: '#10a37f', // Muted green
    accentForeground: '#ffffff',
    muted: '#ececf1',
    mutedForeground: '#565869',
    border: '#d1d5db',
    ring: '#10a37f',
  },
  dark: {
    background: '#0d0d0d',
    foreground: '#ececf1',
    card: '#1a1a1b',
    cardForeground: '#ececf1',
    primary: '#ececf1',
    primaryForeground: '#0d0d0d',
    secondary: '#424245',
    secondaryForeground: '#ececf1',
    accent: '#10a37f', // Muted green
    accentForeground: '#0d0d0d',
    muted: '#424245',
    mutedForeground: '#b4b4b8',
    border: '#424245',
    ring: '#10a37f',
  },
};

export const THEME_COLORS = {
  success: '#10a37f',
  warning: '#f97316',
  error: '#ef4444',
  info: '#0ea5e9',
};

export type ThemeMode = 'light' | 'dark' | 'system';
