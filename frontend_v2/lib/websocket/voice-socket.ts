import { wsClient } from './client';
import { WS_EVENTS } from '../constants';
import { VoiceState } from '@/models';

export const voiceSocket = {
  onVoiceStateChange(handler: (state: { state: VoiceState; sessionId: string }) => void) {
    return wsClient.on(WS_EVENTS.VOICE_STATE, handler);
  },
  onVoiceError(handler: (error: { message: string; code: string }) => void) {
    return wsClient.on('voice:error', handler);
  },
  setVoiceSettings(settings: {
    language?: string;
    timeout?: number;
    enableVAD?: boolean;
    enableNoise?: boolean;
  }) {
    wsClient.send('voice:config', {
      ...settings,
      timestamp: Date.now(),
    });
  },
  getVoiceState(sessionId: string) {
    wsClient.send('voice:get-state', {
      sessionId,
      timestamp: Date.now(),
    });
  },
  offAll() {
    wsClient.off(WS_EVENTS.VOICE_STATE);
    wsClient.off('voice:error');
  },
};
