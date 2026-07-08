export const API_ROUTES = {
  CONVERSATIONS: '/conversations',
  MESSAGES: '/conversations/:id/messages',
  SEND_MESSAGE: '/conversations/:id/messages/send',
  STREAM_MESSAGE: '/conversations/:id/messages/stream',
  REGENERATE_MESSAGE: '/conversations/:id/messages/:messageId/regenerate',
  
  MEMORIES: '/memories',
  MEMORY_DETAIL: '/memories/:id',
  
  REFLECTIONS: '/reflections',
  REFLECTION_DETAIL: '/reflections/:id',
  
  PROFILE: '/profile',
  PROFILE_UPDATE: '/profile',
  
  HOTLINES: '/hotlines',

  
  INSIGHTS: '/insights',
  INSIGHTS_GENERATE: '/insights/generate',
  
  SETTINGS: '/settings',
};

export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  RECONNECT: 'reconnect',
  ERROR: 'error',
  
  CHAT_MESSAGE: 'chat:message',
  CHAT_STREAM_START: 'chat:stream:start',
  CHAT_STREAM_CHUNK: 'chat:stream:chunk',
  CHAT_STREAM_END: 'chat:stream:end',
  
  VOICE_TRANSCRIPT: 'voice:transcript',
  VOICE_TRANSCRIPT_PARTIAL: 'voice:transcript:partial',
  VOICE_STATE: 'voice:state',
  
  NOTIFICATION: 'notification',
  REMINDER: 'reminder',
};

export const LOCAL_STORAGE_KEYS = {
  THEME_MODE: 'companion:theme-mode',
  SIDEBAR_COLLAPSED: 'companion:sidebar-collapsed',
  CHAT_DRAFTS: 'companion:chat-drafts',
  USER_PREFERENCES: 'companion:user-preferences',
};

export const VALIDATION = {
  MESSAGE_MIN_LENGTH: 1,
  MESSAGE_MAX_LENGTH: 4000,
  MEMORY_TITLE_MIN: 1,
  MEMORY_TITLE_MAX: 200,
  MEMORY_CONTENT_MIN: 1,
  MEMORY_CONTENT_MAX: 10000,
};

export const DEBOUNCE_DELAYS = {
  SEARCH: 300,
  AUTO_SAVE: 1000,
  RESIZE: 200,
};

export const ANIMATION_DURATION = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
};

export const EMPTY_STATES = {
  NO_CONVERSATIONS: {
    title: 'No conversations yet',
    description: 'Start a new conversation to begin your journey',
  },
  NO_MEMORIES: {
    title: 'No memories yet',
    description: 'Memories will appear as you chat and reflect',
  },
  NO_REFLECTIONS: {
    title: 'No reflections yet',
    description: 'Begin a reflection to explore your feelings',
  },
  NO_HOTLINES: {
    title: 'No hotline resources',
    description: 'Crisis resources will appear here when configured',
  },
};
