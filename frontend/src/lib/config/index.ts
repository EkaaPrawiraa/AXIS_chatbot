export const APP_CONFIG = {
  name: 'Companion',
  version: '1.0.0',
  description: 'Your personal AI companion for emotional growth and reflection',
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api',
    timeout: 3000000,
  },
  websocket: {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001/ws',
    reconnectAttempts: 5,
    reconnectDelay: 1000,
    heartbeatInterval: 30000,
  },
  voice: {
    enabled: true,
    language: 'en-US',
    sampleRate: 16000,
    timeout: 3000000, // 30 seconds listening timeout
    enableVAD: true,
    enableNoise: true,
  },
  chat: {
    pageSize: 50,
    maxMessageLength: 4000,
    enableMarkdown: true,
    enableCopy: true,
    enableRegenerate: true,
  },
  features: {
    voice: true,
    memory: true,
    reflection: true,
    insights: true,
    reminders: true,
  },
  ui: {
    animationEnabled: true,
    reducedMotion: false,
    toastDuration: 4000,
  },
};

export * from './theme';
