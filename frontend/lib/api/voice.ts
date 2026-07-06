import { apiClient } from './client';
import { SynthesizeSpeechRequest, SynthesizeSpeechResponse, VoiceOption } from '@/models';

export const voiceAPI = {
  synthesize: async (request: SynthesizeSpeechRequest) => {
    const response = await apiClient.post<SynthesizeSpeechResponse>('/voice/synthesize', request);
    return response.data.data!;
  },
  listOptions: async () => {
    const response = await apiClient.get<VoiceOption[]>('/voice/options');
    return response.data.data || [];
  },
};
