import axios, { AxiosInstance, AxiosError } from 'axios';
import { APP_CONFIG } from '../config';
import { APIResponse } from '@/models';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: APP_CONFIG.api.baseUrl,
      timeout: APP_CONFIG.api.timeout,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use(
      (config) => {
        const csrfToken = readCookie('axis_csrf');
        if (csrfToken) {
          config.headers['X-CSRF-Token'] = csrfToken;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as any;
        const status = error.response?.status;
        const isAuthEndpoint =
          typeof config?.url === 'string' &&
          (config.url.includes('/auth/refresh') || config.url.includes('/auth/login'));

        // Coba rotasi access token sekali via refresh token sebelum menyerah.
        if (status === 401 && config && !config._retry && !config.skipAuthRedirect && !isAuthEndpoint) {
          config._retry = true;
          try {
            await this.client.post('/auth/refresh');
            return this.client(config);
          } catch {
            // refresh gagal -> jatuh ke alur logout di bawah
          }
        }

        if (status === 401 && !config?.skipAuthRedirect) {
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth-token');
            const next = window.location.pathname && window.location.pathname !== '/auth'
              ? `?next=${encodeURIComponent(window.location.pathname)}`
              : '';
            window.location.href = `/auth${next}`;
          }
        }
        return Promise.reject(error);
      }
    );
  }

  get<T>(url: string, config?: any) {
    return this.client.get<APIResponse<T>>(url, config);
  }

  post<T>(url: string, data?: any, config?: any) {
    return this.client.post<APIResponse<T>>(url, data, config);
  }

  put<T>(url: string, data?: any, config?: any) {
    return this.client.put<APIResponse<T>>(url, data, config);
  }

  patch<T>(url: string, data?: any, config?: any) {
    return this.client.patch<APIResponse<T>>(url, data, config);
  }

  delete<T>(url: string, config?: any) {
    return this.client.delete<APIResponse<T>>(url, config);
  }
}

export const apiClient = new APIClient();

function readCookie(name: string): string {
  if (typeof document === 'undefined') {
    return '';
  }
  const prefix = `${name}=`;
  const value = document.cookie
    .split('; ')
    .find((part) => part.startsWith(prefix))
    ?.slice(prefix.length);
  return value ? decodeURIComponent(value) : '';
}
