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

const PENDING_DELETE_STORAGE_KEY = 'client-chat-pending-deletes';

function readPendingDeletionIds() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return [];
  }
  const stored = window.localStorage.getItem(PENDING_DELETE_STORAGE_KEY);
  try {
    const parsed = JSON.parse(stored);
    if (Array.isArray(parsed)) {
      return Array.from(
        new Set(
          parsed
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value))
        )
      ).sort((a, b) => a - b);
    }
  } catch (error) {
    console.error('读取待删除会话列表失败', error);
  }
  return [];
}

function persistPendingDeletionIds(ids) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  window.localStorage.setItem(PENDING_DELETE_STORAGE_KEY, JSON.stringify(ids));
}

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
    sendingConversationIds: [],
    pendingMessages: {},
    streamingMessageId: null,
    streamingConversationId: null,
    streamingTimer: null,
    streamingTarget: '',
    streamingDisplayed: '',
    streamingPaused: false,
    streamingPauseReason: null,
    pausedStreams: {},
    sendAbortControllers: {},
    lastSendAttempt: null,
    stoppedThinkingConversationId: null,
    terminatedConversations: {},
    pendingDeletionIds: readPendingDeletionIds()
  }),
  getters: {
    activeConversation(state) {
      return state.conversations.find((item) => item.id === state.activeConversationId) || null;
    },
    isActiveConversationSending(state) {
      return state.activeConversationId != null && state.sendingConversationIds.includes(state.activeConversationId);
    },
    getConversationDomains: (state) => (conversationId) => {
      if (!conversationId) {
        return [];
      }
      const selection = state.conversationDomains[conversationId];
      return Array.isArray(selection) ? [...selection] : [];
    },
    isActiveConversationStreaming(state) {
      return (
        state.streamingConversationId != null &&
        state.streamingConversationId === state.activeConversationId &&
        state.streamingTimer != null &&
        !state.streamingPaused
      );
    },
    isActiveConversationStreamPaused(state) {
      return (
        state.streamingConversationId != null &&
        state.streamingConversationId === state.activeConversationId &&
        state.streamingPaused
      );
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
          this.pendingDeletionIds = [];
          persistPendingDeletionIds(this.pendingDeletionIds);
          return;
        }
        const { data } = await fetchConversations(authStore.user.id);
        const nextDomains = {};
        const pendingDeletionSet = new Set(this.pendingDeletionIds);
        const filteredConversations = data.filter((conversation) => !pendingDeletionSet.has(conversation.id));
        filteredConversations.forEach((conversation) => {
          const existing = this.conversationDomains[conversation.id];
          nextDomains[conversation.id] = Array.isArray(existing)
            ? normalizeDomainIds(existing)
            : [];
        });
        this.conversationDomains = nextDomains;
        this.conversations = filteredConversations;
        if (selectFirst && filteredConversations.length && !this.activeConversationId) {
          this.activeConversationId = filteredConversations[0].id;
          await this.loadMessages(filteredConversations[0].id);
        }
        this.retryPendingDeletes();
      } finally {
        this.isLoading = false;
      }
    },
    async selectConversation(conversationId) {
      const switchingConversation =
        conversationId && this.activeConversationId && this.activeConversationId !== conversationId;
      if (!conversationId) {
        this.stopAssistantStream({ complete: false });
        this.abortActiveSend();
        this.lastSendAttempt = null;
        this.stoppedThinkingConversationId = null;
        this.activeConversationId = null;
        this.messages = [];
        return;
      }

      if (switchingConversation && this.streamingConversationId === this.activeConversationId) {
        this.stopAssistantStream({
          complete: false,
          pause: true,
          reason: this.streamingPauseReason || 'switch'
        });
      }

      this.restorePausedStream(conversationId);
      this.activeConversationId = conversationId;
      await this.loadMessages(conversationId);

      if (
        this.streamingPaused &&
        this.streamingConversationId === conversationId &&
        this.streamingPauseReason === 'switch'
      ) {
        this.resumeAssistantStream();
      }
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
    async sendMessage(conversationId, payload, { reuseMessageId = null } = {}) {
      if (!conversationId) {
        return null;
      }
      if (this.isConversationTerminated(conversationId)) {
        return null;
      }
      const content = payload?.content?.trim();
      if (!content) {
        return null;
      }
      this.stopAssistantStream({ complete: false });
      this.abortActiveSend();
      this.stoppedThinkingConversationId = null;
      const existingPending = reuseMessageId
        ? this.getPendingMessages(conversationId).find((item) => item.id === reuseMessageId)
        : null;
      const existingMessage = reuseMessageId
        ? this.messages.find((item) => item.id === reuseMessageId) || existingPending
        : null;
      const messageId = reuseMessageId || `temp-${Date.now()}`;
      const baseMessage =
        existingMessage ||
        ({
          id: messageId,
          role: payload.role || 'user',
          content,
          created_at: new Date().toISOString(),
          conversation_id: conversationId
        });

      this.lastSendAttempt = {
        conversationId,
        messageId,
        payload: {
          ...payload,
          content
        }
      };

      if (!existingPending) {
        this.addPendingMessage(conversationId, baseMessage);
      }
      const hasMessageInState = this.messages.some((item) => item.id === baseMessage.id);
      if (!hasMessageInState && this.activeConversationId === conversationId) {
        this.messages = normalizeMessages([...this.messages, baseMessage]);
      }
      this.addSendingConversation(conversationId);
      const controller = new AbortController();
      this.setSendAbortController(conversationId, controller);
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
        const { data } = await sendConversationMessage(conversationId, body, { signal: controller.signal });
        this.removePendingMessage(conversationId, messageId);
        if (this.isConversationTerminated(conversationId)) {
          return null;
        }
        if (this.activeConversationId === conversationId) {
          const nextMessages = [...this.messages];
          const index = nextMessages.findIndex((item) => item.id === messageId);
          if (data?.user) {
            if (index !== -1) {
              nextMessages.splice(index, 1, data.user);
            } else {
              nextMessages.push(data.user);
            }
          } else if (index !== -1) {
            nextMessages.splice(index, 1, { ...baseMessage, id: `${messageId}-confirmed` });
          }
          this.messages = normalizeMessages(nextMessages);
          if (data?.assistant) {
            this.startAssistantStream(conversationId, data.assistant);
          }
        }
        return data;
      } catch (error) {
        const isCanceled = error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError';
        if (isCanceled) {
          return null;
        }
        this.removePendingMessage(conversationId, messageId);
        if (this.activeConversationId === conversationId) {
          const index = this.messages.findIndex((item) => item.id === messageId);
          if (index !== -1) {
            const nextMessages = [...this.messages];
            nextMessages.splice(index, 1);
            this.messages = normalizeMessages(nextMessages);
          }
        }
        throw error;
      } finally {
        this.removeSendingConversation(conversationId);
        this.clearSendAbortController(conversationId);
        if (!this.sendingConversationIds.length) {
          const wasStopped = this.stoppedThinkingConversationId === conversationId;
          if (!wasStopped) {
            this.lastSendAttempt = null;
          }
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
    setSendAbortController(conversationId, controller) {
      if (!conversationId) {
        return;
      }
      this.sendAbortControllers = {
        ...this.sendAbortControllers,
        [conversationId]: controller
      };
    },
    clearSendAbortController(conversationId) {
      if (!conversationId) {
        return;
      }
      const { [conversationId]: _removed, ...rest } = this.sendAbortControllers;
      this.sendAbortControllers = rest;
    },
    markConversationTerminated(conversationId) {
      if (!conversationId) {
        return;
      }
      this.terminatedConversations = {
        ...this.terminatedConversations,
        [conversationId]: true
      };
    },
    unmarkConversationTerminated(conversationId) {
      if (!conversationId || !this.terminatedConversations[conversationId]) {
        return;
      }
      const { [conversationId]: _removed, ...rest } = this.terminatedConversations;
      this.terminatedConversations = rest;
    },
    isConversationTerminated(conversationId) {
      if (!conversationId) {
        return false;
      }
      return !!this.terminatedConversations[conversationId];
    },
    abortActiveSend() {
      if (!this.activeConversationId) {
        return;
      }
      const controller = this.sendAbortControllers[this.activeConversationId];
      if (controller) {
        controller.abort();
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
      const prevConversationIndex = this.conversations.findIndex((item) => item.id === conversationId);
      const prevConversation = prevConversationIndex !== -1 ? this.conversations[prevConversationIndex] : null;
      const prevDomains = this.conversationDomains[conversationId];
      const prevPending = this.pendingMessages[conversationId];
      const prevActiveConversationId = this.activeConversationId;
      const prevMessages = this.activeConversationId === conversationId ? [...this.messages] : null;

      this.markConversationTerminated(conversationId);
      this.addPendingDeletionId(conversationId);
      this.stopConversationThinking(conversationId, { skipRestartMark: true, clearSendState: true });
      this.clearPausedStream(conversationId);
      if (this.lastSendAttempt?.conversationId === conversationId) {
        this.lastSendAttempt = null;
      }
      if (this.stoppedThinkingConversationId === conversationId) {
        this.stoppedThinkingConversationId = null;
      }
      if (this.streamingConversationId === conversationId) {
        this.stopAssistantStream({ complete: false });
      }

      const remainingConversations = this.conversations.filter((item) => item.id !== conversationId);
      const nextActiveId =
        this.activeConversationId === conversationId
          ? remainingConversations.length
            ? remainingConversations[0].id
            : null
          : this.activeConversationId;

      this.conversations = remainingConversations;
      const { [conversationId]: _removed, ...restDomains } = this.conversationDomains;
      this.conversationDomains = restDomains;
      const { [conversationId]: _pendingRemoved, ...pendingRest } = this.pendingMessages;
      this.pendingMessages = pendingRest;
      if (this.activeConversationId === conversationId) {
        this.activeConversationId = nextActiveId;
        this.messages = [];
      }
      if (nextActiveId) {
        this.loadMessages(nextActiveId).catch((error) => {
          console.error('加载删除后的默认会话消息失败', error);
        });
      }

      (async () => {
        try {
          await deleteConversation(conversationId);
          this.removePendingDeletionId(conversationId);
        } catch (error) {
          this.removePendingDeletionId(conversationId);
          this.restoreConversationAfterFailedDelete({
            conversationId,
            conversation: prevConversation,
            conversationIndex: prevConversationIndex,
            domains: prevDomains,
            pending: prevPending,
            prevActiveConversationId,
            prevMessages,
            nextActiveId
          });
          console.error('删除会话失败', error);
        } finally {
          this.unmarkConversationTerminated(conversationId);
        }
      })();
    },
    restoreConversationAfterFailedDelete({
      conversationId,
      conversation,
      conversationIndex,
      domains,
      pending,
      prevActiveConversationId,
      prevMessages,
      nextActiveId
    }) {
      if (conversation) {
        const hasConversation = this.conversations.some((item) => item.id === conversationId);
        if (!hasConversation) {
          const nextConversations = [...this.conversations];
          const insertAt = Math.max(0, conversationIndex);
          nextConversations.splice(insertAt, 0, conversation);
          this.conversations = nextConversations;
        }
      }
      if (domains !== undefined) {
        this.conversationDomains = {
          ...this.conversationDomains,
          [conversationId]: normalizeDomainIds(domains)
        };
      }
      if (pending !== undefined) {
        this.pendingMessages = {
          ...this.pendingMessages,
          [conversationId]: [...pending]
        };
      }

      const shouldRestoreActive = this.activeConversationId === nextActiveId || this.activeConversationId == null;
      if (shouldRestoreActive && prevActiveConversationId === conversationId) {
        this.activeConversationId = conversationId;
        if (prevMessages && prevMessages.length) {
          this.messages = [...prevMessages];
        }
      }
    },
    addPendingDeletionId(conversationId) {
      const nextIds = Array.from(new Set([...this.pendingDeletionIds, Number(conversationId)]));
      this.pendingDeletionIds = nextIds;
      persistPendingDeletionIds(this.pendingDeletionIds);
    },
    removePendingDeletionId(conversationId) {
      const nextIds = this.pendingDeletionIds.filter((id) => id !== Number(conversationId));
      if (nextIds.length !== this.pendingDeletionIds.length) {
        this.pendingDeletionIds = nextIds;
        persistPendingDeletionIds(this.pendingDeletionIds);
      }
    },
    retryPendingDeletes() {
      if (!this.pendingDeletionIds.length) {
        return;
      }
      const pendingIds = [...this.pendingDeletionIds];
      pendingIds.forEach((id) => {
        deleteConversation(id)
          .then(() => {
            this.removePendingDeletionId(id);
          })
          .catch((error) => {
            if (error?.response?.status === 404) {
              this.removePendingDeletionId(id);
              return;
            }
            console.error('重试删除会话失败', error);
          });
      });
    },
    stopConversationThinking(conversationId, { skipRestartMark = false, clearSendState = false } = {}) {
      if (!conversationId) {
        this.stopAssistantStream({ complete: false });
        return;
      }
      const controller = this.sendAbortControllers[conversationId];
      const isSending = this.sendingConversationIds.includes(conversationId);
      if (controller && isSending) {
        if (!skipRestartMark && conversationId === this.activeConversationId) {
          this.stoppedThinkingConversationId = conversationId;
        }
        controller.abort();
      }
      if (clearSendState) {
        this.removeSendingConversation(conversationId);
        this.clearSendAbortController(conversationId);
      }
      if (this.streamingConversationId === conversationId) {
        this.stopAssistantStream({ complete: false });
      }
      if (clearSendState) {
        this.clearPausedStream(conversationId);
        if (this.stoppedThinkingConversationId === conversationId) {
          this.stoppedThinkingConversationId = null;
        }
        if (this.lastSendAttempt?.conversationId === conversationId) {
          this.lastSendAttempt = null;
        }
      }
    },
    stopActiveConversationThinking() {
      if (!this.activeConversationId) {
        this.stopAssistantStream({ complete: false });
        return;
      }
      this.stopConversationThinking(this.activeConversationId);
    },
    restartLastAttempt() {
      const attempt = this.lastSendAttempt;
      if (!attempt || attempt.conversationId !== this.activeConversationId) {
        return;
      }
      this.lastSendAttempt = null;
      this.stoppedThinkingConversationId = null;
      return this.sendMessage(attempt.conversationId, attempt.payload, {
        reuseMessageId: attempt.messageId
      });
    },
    startAssistantStream(conversationId, assistant) {
      if (!assistant) {
        return;
      }
      this.clearPausedStream(conversationId);
      if (this.streamingConversationId && this.streamingConversationId !== conversationId) {
        this.stopAssistantStream({ complete: false, pause: true, reason: 'switch' });
      } else {
        this.stopAssistantStream({ complete: false });
      }
      const messageId = assistant.id || `assistant-${Date.now()}`;
      const baseMessage = {
        ...assistant,
        id: messageId,
        content: ''
      };
      const withoutExisting = this.messages.filter((item) => item.id !== messageId);
      this.messages = normalizeMessages([...withoutExisting, baseMessage]);

      const targetText = assistant.content || '';
      if (!targetText) {
        return;
      }

      this.streamingMessageId = messageId;
      this.streamingConversationId = conversationId;
      this.streamingTarget = targetText;
      this.streamingDisplayed = '';
      this.streamingPaused = false;
      this.clearStreamingTimer();

      const totalLength = targetText.length;
      const chunkSize = Math.max(3, Math.ceil(totalLength / 120));
      this.startStreamingInterval(totalLength, chunkSize);
    },
    stopAssistantStream({ complete = false, pause = false, reason = null } = {}) {
      const pauseReason = pause ? reason || 'user' : this.streamingPauseReason;
      const wasPaused = pause
        ? pauseReason === 'switch'
          ? false
          : true
        : this.streamingPaused;
      const pausedState = this.streamingMessageId
        ? {
            conversationId: this.streamingConversationId,
            messageId: this.streamingMessageId,
            target: this.streamingTarget,
            displayed: this.streamingDisplayed,
            pauseReason,
            wasPaused
          }
        : null;
      if (!this.streamingMessageId) {
        this.clearStreamingTimer();
        if (pause) {
          this.streamingPaused = true;
          this.streamingPauseReason = reason || 'user';
        } else {
          this.resetStreamingState();
        }
        return;
      }
      if (complete) {
        this.replaceMessageContent(this.streamingMessageId, this.streamingTarget || this.streamingDisplayed);
      }
      this.clearStreamingTimer();
      if (pause) {
        this.streamingPaused = true;
        this.streamingPauseReason = reason || 'user';
        this.setPausedStream(pausedState);
        return;
      }
      if (this.streamingPaused) {
        this.setPausedStream(pausedState);
      }
      this.resetStreamingState();
    },
    resumeAssistantStream() {
      if (
        !this.streamingPaused ||
        !this.streamingConversationId ||
        this.streamingConversationId !== this.activeConversationId ||
        !this.streamingMessageId ||
        !this.streamingTarget ||
        this.streamingTimer != null
      ) {
        return;
      }
      this.streamingPaused = false;
      this.streamingPauseReason = null;
      this.startStreamingInterval();
    },
    clearStreamingTimer() {
      if (this.streamingTimer != null) {
        window.clearInterval(this.streamingTimer);
        this.streamingTimer = null;
      }
    },
    resetStreamingState() {
      this.streamingMessageId = null;
      this.streamingConversationId = null;
      this.streamingTarget = '';
      this.streamingDisplayed = '';
      this.streamingPaused = false;
      this.streamingPauseReason = null;
    },
    setPausedStream(pausedState) {
      if (!pausedState?.conversationId || !pausedState.messageId) {
        return;
      }
      this.pausedStreams = {
        ...this.pausedStreams,
        [pausedState.conversationId]: {
          messageId: pausedState.messageId,
          target: pausedState.target || '',
          displayed: pausedState.displayed || '',
          pauseReason: pausedState.pauseReason || 'user',
          wasPaused: pausedState.wasPaused === false ? false : true
        }
      };
    },
    clearPausedStream(conversationId) {
      if (!conversationId || !this.pausedStreams[conversationId]) {
        return;
      }
      const { [conversationId]: _removed, ...rest } = this.pausedStreams;
      this.pausedStreams = rest;
    },
    restorePausedStream(conversationId) {
      if (!conversationId) {
        return;
      }
      if (this.streamingConversationId === conversationId && this.streamingPaused) {
        return;
      }
      const paused = this.pausedStreams[conversationId];
      if (!paused) {
        return;
      }
      this.streamingConversationId = conversationId;
      this.streamingMessageId = paused.messageId;
      this.streamingTarget = paused.target || '';
      this.streamingDisplayed = paused.displayed || '';
      const wasPaused = paused.wasPaused === false ? false : true;
      this.streamingPaused = wasPaused;
      this.streamingPauseReason = paused.pauseReason || (wasPaused ? 'user' : null);
      this.clearStreamingTimer();
      this.clearPausedStream(conversationId);
      if (!wasPaused && this.streamingTarget) {
        this.startStreamingInterval();
      }
    },
    startStreamingInterval(existingTotalLength = null, existingChunkSize = null) {
      if (!this.streamingTarget || !this.streamingMessageId) {
        return;
      }
      this.clearStreamingTimer();
      const totalLength = existingTotalLength || this.streamingTarget.length;
      const chunkSize = existingChunkSize || Math.max(3, Math.ceil(totalLength / 120));
      this.streamingTimer = window.setInterval(() => {
        const nextLength = Math.min(this.streamingDisplayed.length + chunkSize, totalLength);
        const nextContent = this.streamingTarget.slice(0, nextLength);
        this.streamingDisplayed = nextContent;
        this.replaceMessageContent(this.streamingMessageId, nextContent);

        if (nextLength >= totalLength) {
          this.stopAssistantStream({ complete: true });
        }
      }, 30);
    },
    addSendingConversation(conversationId) {
      if (!conversationId) {
        return;
      }
      if (this.sendingConversationIds.includes(conversationId)) {
        return;
      }
      this.sendingConversationIds = [...this.sendingConversationIds, conversationId];
    },
    removeSendingConversation(conversationId) {
      if (!conversationId) {
        return;
      }
      if (!this.sendingConversationIds.includes(conversationId)) {
        return;
      }
      this.sendingConversationIds = this.sendingConversationIds.filter((id) => id !== conversationId);
    },
    replaceMessageContent(messageId, nextContent) {
      const index = this.messages.findIndex((item) => item.id === messageId);
      if (index === -1) {
        return;
      }
      const nextMessages = [...this.messages];
      nextMessages.splice(index, 1, { ...nextMessages[index], content: nextContent });
      this.messages = normalizeMessages(nextMessages);
    }
  }
});
