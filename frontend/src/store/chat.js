import { defineStore } from 'pinia';
import {
  fetchConversations,
  createConversation,
  fetchConversationMessages,
  sendConversationMessage
} from '@/services/chat';
import { useUiStore } from './ui';
import { useAuthStore } from './auth';

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
      return (
        state.conversations.find(
          (conv) => conv.id === state.activeConversationId
        ) || null
      );
    }
  },
  actions: {
    async loadConversations() {
      this.isLoading = true;
      try {
        const authStore = useAuthStore();
        if (!authStore.user) {
          this.conversations = [];
          return;
        }
        const { data } = await fetchConversations(authStore.user.id);
        this.conversations = data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to load conversations.'
        });
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
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to load messages.'
        });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async startConversation(payload) {
      this.isSending = true;
      try {
        const authStore = useAuthStore();
        if (!authStore.user) {
          throw new Error('You must be logged in to start a conversation.');
        }
        const { name, prompt } = payload;
        const { data } = await createConversation({
          user_id: authStore.user.id,
          title: name?.trim() || null
        });
        await this.loadConversations();
        this.activeConversationId = data.id;
        this.messages = [];
        if (prompt?.trim()) {
          await this.sendMessage(data.id, {
            content: prompt.trim()
          });
        } else {
          await this.loadMessages(data.id);
        }
        useUiStore().showToast({
          type: 'success',
          message: 'Conversation created.'
        });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to start conversation.'
        });
        throw error;
      } finally {
        this.isSending = false;
      }
    },
    async sendMessage(conversationId, payload) {
      if (!conversationId) return;
      this.isSending = true;
      try {
        const body = {
          chat_id: conversationId,
          role: payload.role || 'user',
          content: payload.content
        };
        if (payload.top_k) {
          body.top_k = payload.top_k;
        }
        if (payload.domain_ids) {
          body.domain_ids = payload.domain_ids;
        }
        const { data } = await sendConversationMessage(conversationId, body);
        if (data?.user) {
          this.messages.push(data.user);
        }
        if (data?.assistant) {
          this.messages.push(data.assistant);
        }
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to send message.'
        });
        throw error;
      } finally {
        this.isSending = false;
      }
    }
  }
});
