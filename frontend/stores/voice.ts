import { create } from 'zustand';
import { VoiceState, Transcript, ID } from '@/models';

interface VoiceStoreState {
  voiceState: VoiceState;
  setVoiceState: (state: VoiceState) => void;
  microphoneAccess: boolean;
  setMicrophoneAccess: (access: boolean) => void;
  currentTranscript: string;
  setCurrentTranscript: (transcript: string) => void;
  appendTranscript: (chunk: string) => void;
  clearTranscript: () => void;
  transcriptConfidence: number;
  setTranscriptConfidence: (confidence: number) => void;
  transcriptHistory: Transcript[];
  addTranscript: (transcript: Transcript) => void;
  clearTranscriptHistory: () => void;
  activeSessionId: ID | null;
  setActiveSessionId: (id: ID | null) => void;
  voiceError: string | null;
  setVoiceError: (error: string | null) => void;
}

export const useVoiceStore = create<VoiceStoreState>((set, get) => ({
  voiceState: 'idle',
  setVoiceState: (state) => set({ voiceState: state }),

  microphoneAccess: false,
  setMicrophoneAccess: (access) => set({ microphoneAccess: access }),

  currentTranscript: '',
  setCurrentTranscript: (transcript) => set({ currentTranscript: transcript }),
  appendTranscript: (chunk) =>
    set((state) => ({ currentTranscript: state.currentTranscript + chunk })),
  clearTranscript: () => set({ currentTranscript: '' }),

  transcriptConfidence: 0,
  setTranscriptConfidence: (confidence) => set({ transcriptConfidence: confidence }),

  transcriptHistory: [],
  addTranscript: (transcript) =>
    set((state) => ({
      transcriptHistory: [...state.transcriptHistory, transcript],
    })),
  clearTranscriptHistory: () => set({ transcriptHistory: [] }),

  activeSessionId: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),

  voiceError: null,
  setVoiceError: (error) => set({ voiceError: error }),
}));
