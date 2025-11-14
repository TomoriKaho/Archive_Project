import { defineStore } from 'pinia';
import {
  fetchConversations,
  createConversation as createConversationRequest,
  updateConversation,
  deleteConversation,
  fetchConversationMessages,
  sendConversationMessage
} from '@/services/chat';
import { useAuthStore } from './auth';

function normalizeDomainIds(rawValue) {
  if (!Array.isArray(rawValue)) {
    return [];
  }
  const cleaned = rawValue
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  return Array.from(new Set(cleaned)).sort((a, b) => a - b);
}

export const useChatStore = defineStore('client-chat', {
  state: () => ({
    conversations: [],
    conversationDomains: {},
    activeConversationId: null,
    messages: [],
    isLoading: false,
    isSending: false
  }),
  getters: {
    activeConversation(state) {
      return state.conversations.find((item) => item.id === state.activeConversationId) || null;
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
    async loadConversations({ selectFirst = false } = {}) {
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
        const nextDomains = {};
        data.forEach((conversation) => {
          const existing = this.conversationDomains[conversation.id];
          nextDomains[conversation.id] = Array.isArray(existing)
            ? normalizeDomainIds(existing)
            : [];
        });
        this.conversationDomains = nextDomains;
        this.conversations = data;
        if (selectFirst && data.length && !this.activeConversationId) {
          this.activeConversationId = data[0].id;
          await this.loadMessages(data[0].id);
        }
      } finally {
        this.isLoading = false;
      }
    },
    async selectConversation(conversationId) {
      if (!conversationId) {
        this.activeConversationId = null;
        this.messages = [];
        return;
      }
      this.activeConversationId = conversationId;
      await this.loadMessages(conversationId);
    },
    async loadMessages(conversationId) {
      if (!conversationId) {
        return;
      }
      this.isLoading = true;
      try {
        const { data } = await fetchConversationMessages(conversationId);
        if (conversationId !== this.activeConversationId) {
          return;
        }
        const pendingMessages = this.messages.filter((item) =>
          typeof item?.id === 'string' && item.id.startsWith('temp-')
        );
        if (pendingMessages.length) {
          const existingIds = new Set(data.map((item) => item.id));
          const merged = [...data];
          pendingMessages.forEach((message) => {
            if (!existingIds.has(message.id)) {
              merged.push(message);
            }
          });
          this.messages = merged;
        } else {
          this.messages = data;
        }
      } finally {
        this.isLoading = false;
      }
    },
    async createConversation({ title, domainIds = [], initialMessage } = {}) {
      const authStore = useAuthStore();
      if (!authStore.user) {
        throw new Error('用户未登录');
      }
      const trimmedTitle = title?.trim();
      const finalTitle = trimmedTitle && trimmedTitle.length ? trimmedTitle : '新的会话';
      const { data } = await createConversationRequest({
        user_id: authStore.user.id,
        title: finalTitle
      });
      await this.loadConversations();
      this.activeConversationId = data.id;
      const normalizedDomains = normalizeDomainIds(domainIds);
      this.setConversationDomains(data.id, normalizedDomains);
      this.messages = [];
      if (initialMessage && initialMessage.trim()) {
        const payload = {
          content: initialMessage,
          domain_ids: normalizedDomains
        };
        this.sendMessage(data.id, payload).catch((error) => {
          console.error('初始消息发送失败', error);
        });
      }
      return data.id;
    },
    async sendMessage(conversationId, payload) {
      if (!conversationId) {
        return null;
      }
      const content = payload?.content?.trim();
      if (!content) {
        return null;
      }
      const tempId = `temp-${Date.now()}`;
      const message = {
        id: tempId,
        role: payload.role || 'user',
        content,
        created_at: new Date().toISOString()
      };
      this.messages.push(message);
      this.isSending = true;
      try {
        const body = {
          chat_id: conversationId,
          role: payload.role || 'user',
          content
        };
        if (payload?.top_k) {
          body.top_k = payload.top_k;
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'domain_ids')) {
          const normalizedDomains = normalizeDomainIds(payload.domain_ids);
          if (normalizedDomains.length) {
            body.domain_ids = normalizedDomains;
          }
        } else {
          const stored = this.getConversationDomains(conversationId);
          if (stored.length) {
            body.domain_ids = stored;
          }
        }
        const { data } = await sendConversationMessage(conversationId, body);
        const index = this.messages.findIndex((item) => item.id === tempId);
        if (data?.user) {
          if (index !== -1) {
            this.messages.splice(index, 1, data.user);
          } else {
            this.messages.push(data.user);
          }
        } else if (index !== -1) {
          this.messages.splice(index, 1, { ...message, id: tempId + '-confirmed' });
        }
        if (data?.assistant) {
          this.messages.push(data.assistant);
        }
        return data;
      } catch (error) {
        const index = this.messages.findIndex((item) => item.id === tempId);
        if (index !== -1) {
          this.messages.splice(index, 1);
        }
        throw error;
      } finally {
        this.isSending = false;
      }
    },
    setConversationDomains(conversationId, domainIds) {
      if (!conversationId) {
        return;
      }
      const normalized = normalizeDomainIds(domainIds);
      this.conversationDomains = {
        ...this.conversationDomains,
        [conversationId]: normalized
      };
    },
    async renameConversation(conversationId, title) {
      if (!conversationId) {
        return null;
      }
      const body = { title: title?.trim() || null };
      const { data } = await updateConversation(conversationId, body);
      const index = this.conversations.findIndex((item) => item.id === conversationId);
      if (index !== -1) {
        this.conversations.splice(index, 1, data);
      }
      if (this.activeConversationId === conversationId) {
        this.activeConversationId = data.id;
      }
      return data;
    },
    async removeConversation(conversationId) {
      if (!conversationId) {
        return;
      }
      await deleteConversation(conversationId);
      const wasActive = this.activeConversationId === conversationId;
      this.conversations = this.conversations.filter((item) => item.id !== conversationId);
      const { [conversationId]: _removed, ...rest } = this.conversationDomains;
      this.conversationDomains = rest;
      if (wasActive) {
        if (this.conversations.length) {
          const nextId = this.conversations[0].id;
          this.activeConversationId = nextId;
          await this.loadMessages(nextId);
        } else {
          this.activeConversationId = null;
          this.messages = [];
        }
      }
    }
  }
});
