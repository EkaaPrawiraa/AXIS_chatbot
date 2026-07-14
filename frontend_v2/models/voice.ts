import { ID } from "./common";

export type VoiceState = "idle" | "listening" | "processing" | "speaking";

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
	type: "partial" | "final";
	content: string;
	confidence: number;
}

export type VoiceOutputModality = "text" | "voice" | "both";
export type TTSModelChoice =
	| "v2_5_turbo"
	| "v3"
	| "openai_tts1"
	| "gemini-3.1-flash-tts"
	| "gemini-2.5-pro-tts"
	| "gemini-3.5-flash-tts";

export interface VoiceTurnRequest {
	output_modality?: VoiceOutputModality;
	audio_input_base64?: string;
	audio_input_mime?: string;
	audio_input_url?: string;
	voice_id?: string;
	tts_model?: TTSModelChoice;
	tts_streaming?: boolean;
}

export interface VoiceTurnResponse {
	transcript?: string;
	transcript_confidence?: number;
	transcript_language?: string;
	output_modality?: VoiceOutputModality;
	voice_id?: string;
	voice_provider_id?: string;
	speech_response?: string;
	speech_response_tags?: string;
	tts_model?: TTSModelChoice;
	tts_provider?: string;
	tts_streaming?: boolean;
	audio_output_base64?: string;
	audio_output_url?: string;
	audio_output_format?: string;
	voice_error?: string;
}

export interface SynthesizeSpeechRequest {
	text: string;
	voice_id?: string;
	tts_model?: TTSModelChoice;
	language_pref?: string;
}

export interface SynthesizeSpeechResponse {
	audio_output_base64?: string;
	audio_output_url?: string;
	audio_output_format?: string;
	tts_provider?: string;
	voice_id?: string;
}

export interface TranscribeSpeechRequest {
	audio_base64: string;
	audio_mime?: string;
	language_pref?: string;
}

export interface TranscribeSpeechResponse {
	text: string;
	language?: string;
	confidence?: number;
	voice_error?: string;
}

export interface VoiceOption {
	id: string;
	name: string;
	provider: string;
	providerId: string;
	category?: string;
	previewUrl?: string;
	description?: string;
}
