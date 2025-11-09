import { defineStore } from 'pinia';
import {
  fetchConversations,
  createConversation,
  updateConversation as updateConversationRequest,
  deleteConversation,
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
        const { name, prompt, domain_ids: rawDomainIds } = payload;
        const domainIds = Array.isArray(rawDomainIds)
          ? rawDomainIds.map((value) => Number(value))
          : [];
        const { data } = await createConversation({
          user_id: authStore.user.id,
          title: name?.trim() || null,
          domain_ids: domainIds.length ? domainIds : null
        });
        await this.loadConversations();
        this.activeConversationId = data.id;
        this.messages = [];
        if (prompt?.trim()) {
          const messagePayload = { content: prompt.trim() };
          if (domainIds.length) {
            messagePayload.domain_ids = domainIds;
          }
          await this.sendMessage(data.id, messagePayload);
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
      const content = payload.content?.trim();
      if (!content) return;

      const tempId = `temp-${Date.now()}`;
      const userMessage = {
        id: tempId,
        role: payload.role || 'user',
        content,
        created_at: new Date().toISOString()
      };
      this.messages.push(userMessage);

      this.isSending = true;
      try {
        const body = {
          chat_id: conversationId,
          role: payload.role || 'user',
          content
        };
        if (payload.top_k) {
          body.top_k = payload.top_k;
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'domain_ids')) {
          body.domain_ids = Array.isArray(payload.domain_ids)
            ? payload.domain_ids.map((value) => Number(value))
            : payload.domain_ids;
        }
        const { data } = await sendConversationMessage(conversationId, body);
        if (data?.user) {
          const index = this.messages.findIndex((msg) => msg.id === tempId);
          if (index !== -1) {
            this.messages.splice(index, 1, data.user);
          } else {
            this.messages.push(data.user);
          }
        }
        if (data?.assistant) {
          this.messages.push(data.assistant);
        }
        return data;
      } catch (error) {
        const index = this.messages.findIndex((msg) => msg.id === tempId);
        if (index !== -1) {
          this.messages.splice(index, 1);
        }
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to send message.'
        });
        throw error;
      } finally {
        this.isSending = false;
      }
    },
    async updateConversation(conversationId, payload) {
      if (!conversationId) return null;
      try {
        const body = {};
        if (Object.prototype.hasOwnProperty.call(payload, 'title')) {
          body.title = payload.title;
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'domain_ids')) {
          body.domain_ids = Array.isArray(payload.domain_ids)
            ? payload.domain_ids.map((value) => Number(value))
            : payload.domain_ids;
        }
        const { data } = await updateConversationRequest(conversationId, body);
        const index = this.conversations.findIndex((item) => item.id === conversationId);
        if (index !== -1) {
          this.conversations.splice(index, 1, data);
        }
        if (this.activeConversationId === conversationId) {
          this.activeConversationId = data.id;
        }
        useUiStore().showToast({
          type: 'success',
          message: 'Conversation updated.'
        });
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to update conversation.'
        });
        throw error;
      }
    },
    async removeConversation(conversationId) {
      if (!conversationId) return;
      const uiStore = useUiStore();
      let notFound = false;
      try {
        await deleteConversation(conversationId);
      } catch (error) {
        if (error?.response?.status === 404) {
          notFound = true;
        } else {
          uiStore.showToast({
            type: 'error',
            message: 'Unable to delete conversation.'
          });
          throw error;
        }
      }

      if (this.activeConversationId === conversationId) {
        this.activeConversationId = null;
        this.messages = [];
      }

      await this.loadConversations();
      if (!this.conversations.length) {
        uiStore.showToast({
          type: 'success',
          message: notFound ? 'Conversation removed.' : 'Conversation deleted.'
        });
        return;
      }
      if (!this.activeConversationId) {
        this.activeConversationId = this.conversations[0].id;
        await this.loadMessages(this.activeConversationId);
      }

      uiStore.showToast({
        type: 'success',
        message: notFound ? 'Conversation removed.' : 'Conversation deleted.'
      });
    }
  }
});
