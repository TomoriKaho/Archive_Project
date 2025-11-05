import { apiClient } from './api';

export function loginRequest(payload) {
  return apiClient.post('/auth/login', payload);
}

export function registerRequest(payload) {
  return apiClient.post('/auth/register', payload);
}

export function fetchCurrentUser() {
  return apiClient.get('/users/me');
}
