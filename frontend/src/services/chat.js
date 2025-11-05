import { apiClient } from './api';

export function fetchConversations() {
  return apiClient.get('/conversations');
}

export function createConversation(payload) {
  return apiClient.post('/conversations', payload);
}

export function fetchConversationMessages(conversationId) {
  return apiClient.get(`/conversations/${conversationId}/messages`);
}

export function sendConversationMessage(conversationId, payload) {
  return apiClient.post(`/conversations/${conversationId}/messages`, payload);
}
