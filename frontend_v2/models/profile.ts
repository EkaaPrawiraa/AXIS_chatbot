import { BaseEntity, ID } from './common';

export type InteractionStyle = 'direct' | 'empathetic' | 'playful' | 'analytical' | 'supportive';
export type ReflectionPreference = 'guided' | 'exploratory' | 'minimal';
export type PreferredResponseModel = 'gpt-5.5' | 'gpt-5.4-nano';
export type Gender = 'pria' | 'wanita';

export interface PersonalityInsight {
  openness: number; // 0-100
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  descriptions: string[]; // Human-readable interpretations
}

export interface UserProfile extends BaseEntity {
  userId: ID;
  name: string;
  interactionStyle: InteractionStyle;
  reflectionPreference: ReflectionPreference;
  companionTraits: string[];
  timezone?: string;
  language: string;
  preferredVoiceId?: string;
  preferredTtsModel?: string;
  preferredResponseModel?: PreferredResponseModel | string;
  gender?: Gender | string;
  safetyTermsAccepted?: boolean;
  safetyTermsVersion?: string;
  safetyTermsAcceptedAt?: number;
  personalityInsight?: PersonalityInsight;
  bio?: string;
  goals?: string[];
}

export interface UpdateProfileRequest {
  name?: string;
  language?: string;
  preferredLanguage?: string;
  preferredVoiceId?: string;
  preferredTtsModel?: string;
  preferredResponseModel?: PreferredResponseModel | string;
  gender?: Gender | string;
  safetyTermsAccepted?: boolean;
  safetyTermsVersion?: string;
}

export const INTERACTION_STYLES: Record<InteractionStyle, string> = {
  direct: 'Direct & straightforward',
  empathetic: 'Empathetic & supportive',
  playful: 'Playful & lighthearted',
  analytical: 'Analytical & logical',
  supportive: 'Supportive & encouraging',
};

export const REFLECTION_PREFERENCES: Record<ReflectionPreference, string> = {
  guided: 'Guided step-by-step',
  exploratory: 'Open exploration',
  minimal: 'Minimal guidance',
};
