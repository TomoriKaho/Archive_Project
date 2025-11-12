import { apiClient } from './api';

export function fetchDocuments(params = {}) {
  return apiClient.get('/documents', { params });
}

export function fetchDocument(documentUuid) {
  return apiClient.get(`/documents/by-uuid/${documentUuid}`);
}

export function fetchDocumentChunks(documentUuid, params = {}) {
  return apiClient.get(`/documents/by-uuid/${documentUuid}/chunks`, { params });
}

export function fetchDocumentContent(documentUuid, params = {}) {
  return apiClient.get(`/documents/by-uuid/${documentUuid}/content`, { params });
}

export function createTextDocument(domainId, payload) {
  return apiClient.post(`/domains/${domainId}/documents`, payload);
}

export function uploadCsvDocument(domainId, formData) {
  return apiClient.post(`/domains/${domainId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
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

export function cancelDocumentIndexing(domainId, documentId) {
  return apiClient.post(
    `/domains/${domainId}/documents/${documentId}/cancel-indexing`
  );
}
