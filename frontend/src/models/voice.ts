import { ID } from './common';

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

export interface Transcript {
  id: ID;
  messageId?: ID;
  content: string;
  isFinal: boolean;
  confidence: number;
  startTime: number;
  endTime?: number;
}

export interface VoiceSession {
  id: ID;
  conversationId: ID;
  startTime: number;
  endTime?: number;
  transcript: Transcript[];
  audioUrl?: string;
  isProcessing: boolean;
}

export interface VoiceConfig {
  language: string;
  enableVAD: boolean; // Voice Activity Detection
  enableNoise: boolean; // Noise suppression
  sampleRate: number;
  timeout: number; // Listening timeout in ms
}

export interface TranscriptChunk {
  type: 'partial' | 'final';
  content: string;
  confidence: number;
}
