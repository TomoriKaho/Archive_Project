import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api';
const TOKEN_STORAGE_KEY =
  process.env.VUE_APP_TOKEN_STORAGE_KEY || 'archive_ai_token';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 0
});

let interceptorsConfigured = false;

export function configureApi(authStore) {
  if (interceptorsConfigured) {
    return;
  }
  interceptorsConfigured = true;
  apiClient.interceptors.request.use((config) => {
    const token = authStore.token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response && [401, 419].includes(error.response.status)) {
        authStore.handleAuthError();
      }
      return Promise.reject(error);
    }
  );
}

export function persistToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}
