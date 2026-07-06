import { apiClient } from './client';
import { AuthResponse, LoginRequest, RegisterRequest } from '@/models';

export const authAPI = {
  login: async (request: LoginRequest) => {
    const response = await apiClient.post<AuthResponse>('/auth/login', request);
    return response.data.data!;
  },

  register: async (request: RegisterRequest) => {
    const response = await apiClient.post<AuthResponse>('/auth/register', request);
    return response.data.data!;
  },

  googleLogin: async (idToken: string) => {
    const response = await apiClient.post<AuthResponse>('/auth/google', { idToken });
    return response.data.data!;
  },

  session: async () => {
    const response = await apiClient.get<AuthResponse>('/auth/session', {
      skipAuthRedirect: true,
    });
    return response.data.data!;
  },

  refresh: async () => {
    const response = await apiClient.post<AuthResponse>('/auth/refresh', undefined, {
      skipAuthRedirect: true,
    });
    return response.data.data!;
  },

  logout: async () => {
    await apiClient.post('/auth/logout', undefined, { skipAuthRedirect: true });
  },

  deleteAccount: async (userId: string, password: string) => {
    await apiClient.post('/account/delete', { userId, password });
  },
};
