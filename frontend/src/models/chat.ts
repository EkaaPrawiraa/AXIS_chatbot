import { BaseEntity, ID, Timestamp } from './common';

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
    references?: string[];
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

export interface ChatStreamEvent {
  type: 'start' | 'content' | 'end' | 'error';
  content?: string;
  messageId?: ID;
  error?: string;
}

export interface SendMessageRequest {
  conversationId: ID;
  content: string;
  voiceUrl?: string;
}

export interface SendMessageResponse {
  messageId: ID;
  conversationId: ID;
}
