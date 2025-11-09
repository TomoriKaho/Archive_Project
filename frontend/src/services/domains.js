import { apiClient } from './api';

export function fetchDomains(params = {}) {
  return apiClient.get('/domains', { params });
}

export function createDomain(payload) {
  return apiClient.post('/domains', payload);
}

export function updateDomain(domainId, payload) {
  return apiClient.patch(`/domains/${domainId}`, payload);
}

export function deleteDomain(domainId) {
  return apiClient.delete(`/domains/${domainId}`);
}
