import { apiClient } from './client';
import {
  SynthesizeSpeechRequest,
  SynthesizeSpeechResponse,
  TranscribeSpeechRequest,
  TranscribeSpeechResponse,
  VoiceOption,
} from '@/models';

export const voiceAPI = {
  synthesize: async (request: SynthesizeSpeechRequest) => {
    const response = await apiClient.post<SynthesizeSpeechResponse>('/voice/synthesize', request);
    return response.data.data!;
  },
  transcribe: async (request: TranscribeSpeechRequest) => {
    const response = await apiClient.post<TranscribeSpeechResponse>('/voice/transcribe', request);
    return response.data.data!;
  },
  listOptions: async () => {
    const response = await apiClient.get<VoiceOption[]>('/voice/options');
    return response.data.data || [];
  },
};
