import { apiClient } from './api';

export function fetchConversations(userId, params = {}) {
  return apiClient.get('/chats', {
    params: { user_id: userId, ...params }
  });
}

export function createConversation(payload) {
  return apiClient.post('/chats', payload);
}

export function updateConversation(conversationId, payload) {
  return apiClient.patch(`/chats/${conversationId}`, payload);
}

export function deleteConversation(conversationId) {
  return apiClient.delete(`/chats/${conversationId}`);
}

export function fetchConversationMessages(conversationId, params = {}) {
  return apiClient.get(`/chats/${conversationId}/messages`, { params });
}

export function sendConversationMessage(conversationId, payload, options = {}) {
  return apiClient.post(`/chats/${conversationId}/messages`, payload, options);
}
