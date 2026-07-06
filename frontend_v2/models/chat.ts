import { BaseEntity, ID, Timestamp } from './common';
import { VoiceTurnRequest, VoiceTurnResponse } from './voice';

export type MessageRole = 'user' | 'assistant';
export type MessageStatus = 'sending' | 'sent' | 'failed';

export interface Message extends BaseEntity {
  conversationId: ID;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  metadata?: {
    voiceUrl?: string;
    emotionDetected?: string;
    safetyFlag?: string;
    crisisTier?: string;
    transcript?: string;
    audioOutputBase64?: string;
    audioOutputUrl?: string;
    audioOutputFormat?: string;
    voice?: VoiceTurnResponse;
    references?: string[];
    phq9?: {
      active: boolean;
      item_id?: number;
      language?: string;
      options?: Array<{ score: number | null; label: string }>;
      phase?: 'offer_pending' | 'offered' | 'in_progress' | 'awaiting_clar' | 'completed' | 'deferred_crisis' | 'declined';
      allow_free_text?: boolean;
      progress?: { current: number; total: number };
    };
  };
}

export interface Conversation extends BaseEntity {
  userId: ID;
  title: string;
  description?: string;
  lastMessageAt: Timestamp;
  messageCount: number;
  preview: string;
}

export interface SendMessageRequest {
  conversationId: ID;
  content: string;
  userId?: ID;
  language_pref?: string;
  preferred_response_model?: string;
  voiceUrl?: string;
  voice?: VoiceTurnRequest;
  phq9_state?: Record<string, unknown>;
  cbt_state?: Record<string, unknown>;
}

export interface SendMessageResponse {
  messageId: ID;
  conversationId: ID;
  userMessage: Message;
  assistantMessage: Message;
  reply: string;
  safety_flag?: string;
  crisis_tier?: string;
  phq9_state?: Record<string, unknown>;
  cbt_state?: Record<string, unknown>;
  voice?: VoiceTurnResponse;
}

export type ChatResponseMode = 'normal' | 'stream';

export type ChatStreamEvent =
  | { event: 'token'; data: string }
  | { event: 'done'; data: SendMessageResponse }
  | { event: 'error'; data: string };
