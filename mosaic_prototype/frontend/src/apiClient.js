import axios from 'axios';
import { API_BASE_URL } from './config';
import { getAuthHeaders, logout, refreshToken, getFriendlyMessage } from './services/authService';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

function isAuthEndpoint(url = '') {
  return url.includes('/login') || url.includes('/register');
}

apiClient.interceptors.request.use(
  (config) => {
    const nextConfig = { ...config };
    if (!isAuthEndpoint(nextConfig.url)) {
      const headers = getAuthHeaders();
      nextConfig.headers = {
        ...nextConfig.headers,
        ...headers,
      };
    }
    return nextConfig;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response } = error || {};
    const config = error?.config || {};
    const payload = response?.data?.error;
    if (payload && payload.message) {
      error.message = payload.message;
      error.code = payload.code;
      error.details = payload.details;
      error.friendlyMessage = getFriendlyMessage(payload.code, payload.message);
    }

    if (response && (response.status === 401 || response.status === 403)) {
      const code = payload?.code;
      try {
        if (code === 'token_expired') {
          await refreshToken();
        } else if (code === 'unauthorized') {
          logout({ silent: true });
          window.location.assign('/login');
        } else if (code === 'invalid_csrf') {
          logout({ silent: true });
          window.location.assign('/login');
        }
      } catch (refreshError) {
        logout({ silent: true });
        window.location.assign('/login');
      }
    }

    const status = response?.status;
    const shouldNotify =
      !config.skipErrorNotification && (!status || status >= 500);
    const friendlyMessage =
      error?.friendlyMessage || error?.message || 'Unexpected error occurred.';
    if (shouldNotify && typeof window !== 'undefined' && friendlyMessage) {
      window.dispatchEvent(
        new CustomEvent('mosaic-api-error', {
          detail: {
            message: friendlyMessage,
            status,
            code: error?.code,
            url: config?.url,
            method: config?.method,
          },
        })
      );
    }

    return Promise.reject(error);
  }
);

export default apiClient;
