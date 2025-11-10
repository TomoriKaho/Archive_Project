import { apiClient } from './api';

export function fetchDocuments(params = {}) {
  return apiClient.get('/documents', { params });
}

export function fetchDocument(documentUuid) {
  return apiClient.get(`/documents/by-uuid/${documentUuid}`);
}

export function fetchDocumentChunks(documentUuid) {
  return apiClient.get(`/documents/by-uuid/${documentUuid}/chunks`);
}

export function createTextDocument(domainId, payload) {
  return apiClient.post(`/domains/${domainId}/documents`, payload);
}

export function uploadCsvDocument(domainId, formData, config = {}) {
  const headers = {
    'Content-Type': 'multipart/form-data',
    ...(config.headers ?? {})
  };
  return apiClient.post(`/domains/${domainId}/documents`, formData, {
    ...config,
    headers
  });
}

export function updateDocument(domainId, documentId, payload) {
  return apiClient.patch(
    `/domains/${domainId}/documents/${documentId}`,
    payload
  );
}

export function deleteDocument(domainId, documentId) {
  return apiClient.delete(`/domains/${domainId}/documents/${documentId}`);
}
