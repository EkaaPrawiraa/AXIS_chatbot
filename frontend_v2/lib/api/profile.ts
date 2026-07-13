import { apiClient } from './client';
import { UserProfile, UpdateProfileRequest, ID } from '@/models';
import { API_ROUTES } from '../constants';

export const profileAPI = {
  getProfile: async (userId: ID) => {
    const response = await apiClient.get<UserProfile>(API_ROUTES.PROFILE, {
      params: { userId },
    });
    return response.data.data!;
  },

  updateProfile: async (userId: ID, request: UpdateProfileRequest) => {
    const response = await apiClient.put<UserProfile>(API_ROUTES.PROFILE_UPDATE, {
      userId,
      ...request,
      preferredLanguage: request.preferredLanguage || request.language,
      preferredVoiceId: request.preferredVoiceId,
      preferredTtsModel: request.preferredTtsModel,
      preferredResponseModel: request.preferredResponseModel,
      safetyTermsAccepted: request.safetyTermsAccepted,
      safetyTermsVersion: request.safetyTermsVersion,
    });
    return response.data.data!;
  },
};
