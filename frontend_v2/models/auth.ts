import { Gender, UserProfile } from './profile';
import { ID, Timestamp } from './common';

export interface AuthUser {
  id: ID;
  email: string;
  displayName: string;
  preferredLanguage: string;
  preferredVoiceId?: string;
  preferredTtsModel?: string;
  preferredResponseModel?: string;
  gender?: Gender | string;
  safetyTermsAccepted: boolean;
  safetyTermsVersion?: string;
  safetyTermsAcceptedAt?: Timestamp;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
  ttl: number;
  profile: UserProfile;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  displayName: string;
  preferredLanguage?: string;
  safetyTermsAccepted?: boolean;
  safetyTermsVersion?: string;
}
