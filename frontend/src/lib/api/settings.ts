import { apiClient } from './client';
import { ID } from '@/models';
import { API_ROUTES } from '../constants';

export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notificationsEnabled: boolean;
  reminderFrequency: 'never' | 'daily' | 'weekly' | 'monthly';
  soundEnabled: boolean;
  dataPrivacy: {
    shareAnalytics: boolean;
    retentionDays: number;
  };
}

export const settingsAPI = {
  getSettings: async (userId: ID) => {
    const response = await apiClient.get<UserSettings>(API_ROUTES.SETTINGS, {
      params: { userId },
    });
    return response.data.data!;
  },

  updateSettings: async (userId: ID, settings: Partial<UserSettings>) => {
    const response = await apiClient.put<UserSettings>(API_ROUTES.SETTINGS, {
      userId,
      ...settings,
    });
    return response.data.data!;
  },

  exportData: async (userId: ID) => {
    const response = await apiClient.post(
      '/settings/export-data',
      { userId },
      { responseType: 'blob' }
    );
    return response.data;
  },

  deleteAccount: async (userId: ID, password: string) => {
    const response = await apiClient.post('/settings/delete-account', {
      userId,
      password,
    });
    return response.data.success;
  },
};
