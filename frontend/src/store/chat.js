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
import { i18n } from '@/i18n';

function normalizeDomainIds(rawValue) {
  if (!Array.isArray(rawValue)) {
    return [];
  }
  const cleaned = rawValue
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  return Array.from(new Set(cleaned)).sort((a, b) => a - b);
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    activeConversationId: null,
    messages: [],
    isLoading: false,
    isSending: false,
    conversationDomains: {}
  }),
  getters: {
    activeConversation(state) {
      return (
        state.conversations.find(
          (conv) => conv.id === state.activeConversationId
        ) || null
      );
    },
    getConversationDomains: (state) => (conversationId) => {
      if (!conversationId) {
        return [];
      }
      const selection = state.conversationDomains[conversationId];
      return Array.isArray(selection) ? [...selection] : [];
    }
  },
  actions: {
    async loadConversations() {
      this.isLoading = true;
      try {
        const authStore = useAuthStore();
        if (!authStore.user) {
          this.conversations = [];
          this.conversationDomains = {};
          this.activeConversationId = null;
          this.messages = [];
          return;
        }
        const { data } = await fetchConversations(authStore.user.id);
        const previousDomains = this.conversationDomains;
        const nextDomains = {};
        data.forEach((conversation) => {
          const existing = previousDomains[conversation.id];
          nextDomains[conversation.id] = Array.isArray(existing)
            ? normalizeDomainIds(existing)
            : [];
        });
        this.conversationDomains = nextDomains;
        this.conversations = data;
        if (
          this.activeConversationId &&
          !data.some((conversation) => conversation.id === this.activeConversationId)
        ) {
          this.activeConversationId = null;
          this.messages = [];
        }
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('chat.toast.loadError')
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
          message: i18n.global.t('chat.toast.messagesError')
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
          throw new Error(i18n.global.t('chat.errors.notAuthenticated'));
        }
        const { name, prompt, domain_ids: rawDomainIds } = payload;
        const domainIds = normalizeDomainIds(rawDomainIds);
        const trimmedName = name?.trim();
        const conversationTitle =
          trimmedName && trimmedName.length
            ? trimmedName
            : i18n.global.t('chat.new.defaultTitle');
        const { data } = await createConversation({
          user_id: authStore.user.id,
          title: conversationTitle
        });
        await this.loadConversations();
        this.setConversationDomains(data.id, domainIds, { notify: false });
        this.activeConversationId = data.id;
        this.messages = [];
        const trimmedPrompt = prompt?.trim();
        if (trimmedPrompt) {
          await sendConversationMessage(data.id, {
            chat_id: data.id,
            role: 'system',
            content: trimmedPrompt
          });
        }
        await this.loadMessages(data.id);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('chat.toast.createSuccess')
        });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('chat.toast.createError')
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
          const normalizedDomains = normalizeDomainIds(payload.domain_ids);
          if (normalizedDomains.length) {
            body.domain_ids = normalizedDomains;
          }
        } else {
          const selection = this.getConversationDomains(conversationId);
          if (selection.length) {
            body.domain_ids = [...selection];
          }
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
          message: i18n.global.t('chat.toast.sendError')
        });
        throw error;
      } finally {
        this.isSending = false;
      }
    },
    setConversationDomains(conversationId, domainIds, options = {}) {
      if (!conversationId) return;
      const normalized = normalizeDomainIds(domainIds);
      this.conversationDomains = {
        ...this.conversationDomains,
        [conversationId]: normalized
      };
      if (options.notify) {
        useUiStore().showToast({
          type: 'success',
          message: normalized.length
            ? i18n.global.t('chat.toast.domainApplied')
            : i18n.global.t('chat.toast.domainCleared')
        });
      }
    },
    async updateConversation(conversationId, payload) {
      if (!conversationId) return null;
      try {
        const body = {};
        if (Object.prototype.hasOwnProperty.call(payload, 'title')) {
          const title = payload.title ?? '';
          const normalizedTitle = title.trim();
          body.title = normalizedTitle || null;
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
          message: i18n.global.t('chat.toast.updateSuccess')
        });
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('chat.toast.updateError')
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
            message: i18n.global.t('chat.toast.deleteError')
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
          message: notFound
            ? i18n.global.t('chat.toast.deleteMissing')
            : i18n.global.t('chat.toast.deleteSuccess')
        });
        return;
      }
      if (!this.activeConversationId) {
        this.activeConversationId = this.conversations[0].id;
        await this.loadMessages(this.activeConversationId);
      }

      uiStore.showToast({
        type: 'success',
        message: notFound
          ? i18n.global.t('chat.toast.deleteMissing')
          : i18n.global.t('chat.toast.deleteSuccess')
      });
    }
  }
});
