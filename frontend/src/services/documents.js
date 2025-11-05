import { apiClient } from './api';

export function fetchDocuments(params = {}) {
  return apiClient.get('/documents', { params });
}

export function fetchDocument(documentId) {
  return apiClient.get(`/documents/${documentId}`);
}

export function createTextDocument(payload) {
  return apiClient.post('/documents', payload);
}

export function uploadCsvDocument(formData) {
  return apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

export function updateDocument(documentId, payload) {
  return apiClient.put(`/documents/${documentId}`, payload);
}

export function deleteDocument(documentId) {
  return apiClient.delete(`/documents/${documentId}`);
}
