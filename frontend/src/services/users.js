import { apiClient } from './api';

export function fetchUsers(params = {}) {
  return apiClient.get('/users', { params });
}

export function updateUser(userId, payload) {
  return apiClient.patch(`/users/${userId}`, payload);
}

export function inviteUser(payload) {
  return apiClient.post('/users/invite', payload);
}
