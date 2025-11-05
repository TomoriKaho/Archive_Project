import { defineStore } from 'pinia';
import {
  fetchConversations,
  createConversation,
  fetchConversationMessages,
  sendConversationMessage
} from '@/services/chat';
import { useUiStore } from './ui';

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    activeConversationId: null,
    messages: [],
    isLoading: false,
    isSending: false
  }),
  getters: {
    activeConversation(state) {
      return state.conversations.find((conv) => conv.id === state.activeConversationId) || null;
    }
  },
  actions: {
    async loadConversations() {
      this.isLoading = true;
      try {
        const { data } = await fetchConversations();
        this.conversations = data;
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Unable to load conversations.' });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async selectConversation(conversationId) {
      this.activeConversationId = conversationId;
      await this.loadMessages(conversationId);
    },
    async loadMessages(conversationId) {
      if (!conversationId) return;
      this.isLoading = true;
      try {
        const { data } = await fetchConversationMessages(conversationId);
        this.messages = data;
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Failed to load messages.' });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async startConversation(payload) {
      this.isSending = true;
      try {
        const { data } = await createConversation(payload);
        await this.loadConversations();
        this.activeConversationId = data.id;
        await this.loadMessages(data.id);
        useUiStore().showToast({ type: 'success', message: 'Conversation created.' });
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Unable to start conversation.' });
        throw error;
      } finally {
        this.isSending = false;
      }
    },
    async sendMessage(conversationId, payload) {
      if (!conversationId) return;
      this.isSending = true;
      try {
        const { data } = await sendConversationMessage(conversationId, payload);
        this.messages.push(data);
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Unable to send message.' });
        throw error;
      } finally {
        this.isSending = false;
      }
    }
  }
});
