import { wsClient } from './client';
import { WS_EVENTS } from '../constants';
import { TranscriptChunk } from '@/models';

export const transcriptSocket = {
  onPartialTranscript(handler: (data: TranscriptChunk) => void) {
    return wsClient.on(WS_EVENTS.VOICE_TRANSCRIPT_PARTIAL, handler);
  },
  onFinalTranscript(handler: (data: TranscriptChunk) => void) {
    return wsClient.on(WS_EVENTS.VOICE_TRANSCRIPT, handler);
  },
  startTranscription(sessionId: string, language: string = 'en-US') {
    wsClient.send('voice:start', {
      sessionId,
      language,
      timestamp: Date.now(),
    });
  },
  stopTranscription(sessionId: string) {
    wsClient.send('voice:stop', {
      sessionId,
      timestamp: Date.now(),
    });
  },
  sendAudioChunk(sessionId: string, audioData: Blob) {
    wsClient.send('voice:audio-chunk', {
      sessionId,
      audio: audioData, // Would be base64 encoded in reality
      timestamp: Date.now(),
    });
  },
  offAll() {
    wsClient.off(WS_EVENTS.VOICE_TRANSCRIPT);
    wsClient.off(WS_EVENTS.VOICE_TRANSCRIPT_PARTIAL);
  },
};
