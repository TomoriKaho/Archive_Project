import { apiClient } from './api';

export function fetchConversations(userId, params = {}) {
  return apiClient.get('/chats', {
    params: { user_id: userId, ...params }
  });
}

export function createConversation(payload) {
  return apiClient.post('/chats', payload);
}

export function fetchConversationMessages(conversationId, params = {}) {
  return apiClient.get(`/chats/${conversationId}/messages`, { params });
}

export function sendConversationMessage(conversationId, payload) {
  return apiClient.post(`/chats/${conversationId}/messages`, payload);
}
