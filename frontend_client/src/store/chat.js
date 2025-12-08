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
import { usePreferencesStore } from './preferences';

function normalizeDomainIds(rawValue) {
  if (!Array.isArray(rawValue)) {
    return [];
  }
  const cleaned = rawValue
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  return Array.from(new Set(cleaned)).sort((a, b) => a - b);
}

const rolePriority = {
  user: 0,
  assistant: 1,
  system: 2
};

function normalizeMessages(messages = []) {
  return [...messages].sort((a, b) => {
    const timeA = new Date(a?.created_at ?? '').getTime();
    const timeB = new Date(b?.created_at ?? '').getTime();
    const hasValidTimeA = !Number.isNaN(timeA);
    const hasValidTimeB = !Number.isNaN(timeB);

    if (hasValidTimeA && hasValidTimeB) {
      if (timeA !== timeB) {
        return timeA - timeB;
      }
    } else if (hasValidTimeA) {
      return -1;
    } else if (hasValidTimeB) {
      return 1;
    }

    const roleA = rolePriority[a?.role] ?? Number.MAX_SAFE_INTEGER;
    const roleB = rolePriority[b?.role] ?? Number.MAX_SAFE_INTEGER;
    if (roleA !== roleB) {
      return roleA - roleB;
    }

    return String(a?.id ?? '').localeCompare(String(b?.id ?? ''));
  });
}

function mergeMessages(base = [], additions = []) {
  const existingIds = new Set(base.map((item) => item.id));
  const merged = [...base];
  additions.forEach((message) => {
    if (!existingIds.has(message.id)) {
      merged.push(message);
    }
  });
  return merged;
}

export const useChatStore = defineStore('client-chat', {
  state: () => ({
    conversations: [],
    conversationDomains: {},
    activeConversationId: null,
    messages: [],
    isLoading: false,
    isSending: false,
    sendingConversationId: null,
    pendingMessages: {}
  }),
  getters: {
    activeConversation(state) {
      return state.conversations.find((item) => item.id === state.activeConversationId) || null;
    },
    isActiveConversationSending(state) {
      return (
        state.isSending &&
        state.activeConversationId != null &&
        state.activeConversationId === state.sendingConversationId
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
    async loadConversations({ selectFirst = false } = {}) {
      this.isLoading = true;
      try {
        const authStore = useAuthStore();
        if (!authStore.user) {
          this.conversations = [];
          this.conversationDomains = {};
          this.activeConversationId = null;
          this.messages = [];
          this.pendingMessages = {};
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
        const pendingMessages = this.getPendingMessages(conversationId);
        const existingMessages = pendingMessages.length ? mergeMessages(data, pendingMessages) : data;
        this.messages = normalizeMessages(existingMessages);
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
      const preferencesStore = usePreferencesStore();
      const defaultTitle = preferencesStore.language === 'en' ? 'New Conversation' : '新会话';
      const finalTitle = trimmedTitle && trimmedTitle.length ? trimmedTitle : defaultTitle;
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
        created_at: new Date().toISOString(),
        conversation_id: conversationId
      };
      this.addPendingMessage(conversationId, message);
      if (this.activeConversationId === conversationId) {
        this.messages = normalizeMessages([...this.messages, message]);
      }
      this.isSending = true;
      this.sendingConversationId = conversationId;
      try {
        const body = {
          chat_id: conversationId,
          role: payload.role || 'user',
          content
        };
        const preferencesStore = usePreferencesStore();
        body.language = preferencesStore.language === 'en' ? 'en' : 'zh';
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
        this.removePendingMessage(conversationId, tempId);
        if (this.activeConversationId === conversationId) {
          const nextMessages = [...this.messages];
          const index = nextMessages.findIndex((item) => item.id === tempId);
          if (data?.user) {
            if (index !== -1) {
              nextMessages.splice(index, 1, data.user);
            } else {
              nextMessages.push(data.user);
            }
          } else if (index !== -1) {
            nextMessages.splice(index, 1, { ...message, id: tempId + '-confirmed' });
          }
          if (data?.assistant) {
            nextMessages.push(data.assistant);
          }
          this.messages = normalizeMessages(nextMessages);
        }
        return data;
      } catch (error) {
        this.removePendingMessage(conversationId, tempId);
        if (this.activeConversationId === conversationId) {
          const index = this.messages.findIndex((item) => item.id === tempId);
          if (index !== -1) {
            const nextMessages = [...this.messages];
            nextMessages.splice(index, 1);
            this.messages = normalizeMessages(nextMessages);
          }
        }
        throw error;
      } finally {
        this.isSending = false;
        if (this.sendingConversationId === conversationId) {
          this.sendingConversationId = null;
        }
      }
    },
    addPendingMessage(conversationId, message) {
      if (!conversationId || !message) {
        return;
      }
      const pending = this.getPendingMessages(conversationId);
      this.pendingMessages = {
        ...this.pendingMessages,
        [conversationId]: [...pending, message]
      };
    },
    removePendingMessage(conversationId, messageId) {
      if (!conversationId || !messageId) {
        return;
      }
      const pending = this.getPendingMessages(conversationId).filter((item) => item.id !== messageId);
      if (pending.length) {
        this.pendingMessages = {
          ...this.pendingMessages,
          [conversationId]: pending
        };
      } else {
        const { [conversationId]: _removed, ...rest } = this.pendingMessages;
        this.pendingMessages = rest;
      }
    },
    getPendingMessages(conversationId) {
      if (!conversationId) {
        return [];
      }
      const pending = this.pendingMessages[conversationId];
      return Array.isArray(pending) ? [...pending] : [];
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
      const { [conversationId]: _pendingRemoved, ...pendingRest } = this.pendingMessages;
      this.pendingMessages = pendingRest;
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
