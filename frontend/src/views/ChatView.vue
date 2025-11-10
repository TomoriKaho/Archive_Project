<template>
  <section class="chat">
    <aside class="chat__sidebar">
      <header class="chat__header">
        <h2>Conversations</h2>
        <button class="button" type="button" @click="openNewConversation">
          New
        </button>
      </header>
      <ul class="chat__conversation-list">
        <li
          v-for="conversation in chatStore.conversations"
          :key="conversation.id"
          :class="{
            'chat__conversation--active':
              conversation.id === chatStore.activeConversationId
          }"
        >
          <button
            type="button"
            class="chat__conversation-trigger"
            @click="selectConversation(conversation.id)"
          >
            <span class="chat__conversation-name">{{
              conversation.title || 'Untitled conversation'
            }}</span>
            <span class="chat__conversation-date">{{
              formatDate(conversation.updated_at)
            }}</span>
          </button>
          <button
            v-if="conversation.id"
            type="button"
            class="chat__conversation-delete"
            :disabled="conversation.id === deletingConversationId"
            @click.stop="promptRemoveConversation(conversation.id)"
            aria-label="Delete conversation"
          >
            {{
              conversation.id === deletingConversationId
                ? 'Deleting…'
                : 'Delete'
            }}
          </button>
        </li>
      </ul>
    </aside>

    <div v-if="hasActiveConversation" class="chat__main">
      <header class="chat__main-header">
        <p class="chat__filter-summary">{{ activeConversationFilterText }}</p>
        <button
          v-if="domainOptions.length"
          class="button button--ghost chat__filter-trigger"
          type="button"
          @click="openDomainFilter"
        >
          Manage domain filter
          <span v-if="domainSelectionChanged" class="chat__filter-indicator">
            •
          </span>
        </button>
      </header>

      <div class="chat__messages" ref="messagesContainer">
        <p v-if="chatStore.messages.length === 0" class="chat__empty">
          No messages yet. Start the conversation by sending a message.
        </p>
        <div
          v-for="message in chatStore.messages"
          :key="message.id"
          class="chat__message"
          :class="`chat__message--${message.role}`"
        >
          <div class="chat__message-meta">
            <span>{{ message.role === 'user' ? 'You' : 'Assistant' }}</span>
            <time>{{ formatDate(message.created_at) }}</time>
          </div>
          <div class="chat__message-content">{{ message.content }}</div>
        </div>
        <div v-if="chatStore.isSending" class="chat__stream">
          Assistant is typing…
        </div>
      </div>

      <form class="chat__composer" @submit.prevent="sendMessage">
        <textarea
          v-model="message"
          rows="3"
          placeholder="Type your message and press send"
          @keydown.enter.exact.prevent="sendMessage"
        ></textarea>
        <button
          class="button button--primary"
          type="submit"
          :disabled="!canSend"
        >
          Send
        </button>
      </form>
    </div>

    <div v-else class="chat__placeholder">
      <h3 class="chat__placeholder-title">No conversation selected</h3>
      <p class="chat__placeholder-text">
        {{
          hasConversations
            ? 'Choose a conversation from the list or start a new one to begin.'
            : 'Create a new conversation to start chatting.'
        }}
      </p>
    </div>

    <BaseModal v-model="isNewConversationOpen" title="Start New Conversation">
      <div
        class="form-field"
        :class="{ 'form-field--error': newConversationErrors.name }"
      >
        <label for="conversation-name">Conversation Title</label>
        <input
          id="conversation-name"
          v-model.trim="newConversationForm.name"
          type="text"
        />
        <p v-if="newConversationErrors.name" class="form-field__error">
          {{ newConversationErrors.name }}
        </p>
      </div>
      <div class="form-field">
        <label for="conversation-prompt">Initial Prompt (optional)</label>
        <textarea
          id="conversation-prompt"
          v-model="newConversationForm.prompt"
          rows="4"
        ></textarea>
      </div>
      <div v-if="domainOptions.length" class="form-field">
        <label>Domain filter (optional)</label>
        <p class="form-field__hint">
          Pick domains to constrain retrieval. Leave empty to include all
          domains.
        </p>
        <div class="chat__domain-options">
          <label
            v-for="domain in domainOptions"
            :key="`new-${domain.id}`"
            class="chat__domain-option"
          >
            <input
              type="checkbox"
              :value="domain.id"
              :checked="newConversationForm.domain_ids.includes(domain.id)"
              @change="toggleNewConversationDomain(domain.id)"
            />
            <span>{{ domain.name }}</span>
          </label>
        </div>
        <button
          class="button button--ghost"
          type="button"
          @click="clearNewConversationDomains"
          :disabled="newConversationForm.domain_ids.length === 0"
        >
          Clear selection
        </button>
      </div>
      <template #footer>
        <button class="button" type="button" @click="closeNewConversation">
          Cancel
        </button>
        <button
          class="button button--primary"
          type="button"
          @click="startConversation"
        >
          {{ chatStore.isSending ? 'Starting…' : 'Start Conversation' }}
        </button>
      </template>
    </BaseModal>

    <BaseModal
      v-if="domainOptions.length"
      v-model="isDomainFilterOpen"
      title="Domain filter"
    >
      <p class="chat__domain-filter-hint">
        Leave unselected to search across every domain.
      </p>
      <div class="chat__domain-options">
        <label
          v-for="domain in domainOptions"
          :key="`active-${domain.id}`"
          class="chat__domain-option"
        >
          <input
            type="checkbox"
            :value="domain.id"
            :checked="activeDomainSelection.includes(domain.id)"
            @change="toggleActiveDomain(domain.id)"
          />
          <span>{{ domain.name }}</span>
        </label>
      </div>
      <template #footer>
        <div class="chat__domain-filter-footer">
          <span class="chat__domain-filter-status">
            {{ activeDomainStatusText }}
            <span
              v-if="domainSelectionChanged"
              class="chat__domain-filter-dirty"
            >
              Unsaved changes — apply to update this conversation
            </span>
          </span>
          <div class="chat__domain-filter-actions">
            <button
              class="button button--ghost"
              type="button"
              @click="clearActiveDomainSelection"
              :disabled="!hasActiveDomainSelection"
            >
              Clear selection
            </button>
            <button
              class="button"
              type="button"
              @click="applyActiveDomains"
              :disabled="!canApplyDomainSelection"
            >
              Apply
            </button>
          </div>
        </div>
      </template>
    </BaseModal>

    <BaseModal v-model="isDeleteConversationOpen" title="Delete Conversation">
      <p>
        Are you sure you want to delete this conversation? This action cannot be
        undone and will remove all messages inside it.
      </p>
      <template #footer>
        <button class="button" type="button" @click="closeDeleteConversation">
          Cancel
        </button>
        <button
          class="button button--danger"
          type="button"
          :disabled="deletingConversationId !== null"
          @click="removeConversation"
        >
          {{ deletingConversationId ? 'Deleting…' : 'Delete conversation' }}
        </button>
      </template>
    </BaseModal>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';

import BaseModal from '@/components/BaseModal.vue';
import { useAuthStore } from '@/store/auth';
import { useChatStore } from '@/store/chat';
import { useDomainsStore } from '@/store/domains';

const authStore = useAuthStore();
const chatStore = useChatStore();
const domainsStore = useDomainsStore();
const message = ref('');
const messagesContainer = ref(null);
const isDomainFilterOpen = ref(false);

const deletingConversationId = ref(null);
const confirmingConversationId = ref(null);
const isDeleteConversationOpen = ref(false);

const isNewConversationOpen = ref(false);
const newConversationForm = reactive({
  name: '',
  prompt: '',
  domain_ids: []
});
const newConversationErrors = reactive({
  name: '',
  prompt: ''
});

const activeDomainSelection = ref([]);

const domainOptions = computed(() =>
  domainsStore.items.slice().sort((a, b) => a.name.localeCompare(b.name))
);

function normalizeDomainIds(value) {
  if (!value || !Array.isArray(value)) {
    return [];
  }
  const normalized = value
    .map((item) => Number(item))
    .filter((item) => !Number.isNaN(item));
  return Array.from(new Set(normalized)).sort((a, b) => a - b);
}

function areDomainSelectionsEqual(first, second) {
  const left = normalizeDomainIds(first);
  const right = normalizeDomainIds(second);
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

const hasActiveConversation = computed(() => !!chatStore.activeConversationId);

const hasConversations = computed(() => chatStore.conversations.length > 0);

const hasActiveDomainSelection = computed(
  () => activeDomainSelection.value.length > 0
);

const storedDomainSelection = computed(() =>
  chatStore.getConversationDomains(chatStore.activeConversationId)
);

const domainNamesById = computed(() => {
  return domainsStore.items.reduce((map, domain) => {
    map.set(Number(domain.id), domain.name);
    return map;
  }, new Map());
});

const appliedDomainNames = computed(() => {
  const selection = normalizeDomainIds(storedDomainSelection.value);
  return selection
    .map((id) => domainNamesById.value.get(id))
    .filter((name) => !!name);
});

const activeConversationFilterText = computed(() => {
  if (!hasActiveConversation.value) {
    return 'Select a conversation to configure domain filters.';
  }
  if (!domainsStore.items.length) {
    return 'Domain filters unavailable.';
  }
  if (appliedDomainNames.value.length === 0) {
    return 'Filter: All domains';
  }
  return `Filter: ${appliedDomainNames.value.join(', ')}`;
});

const domainSelectionChanged = computed(
  () =>
    hasActiveConversation.value &&
    !areDomainSelectionsEqual(
      storedDomainSelection.value,
      activeDomainSelection.value
    )
);

const canApplyDomainSelection = computed(
  () => hasActiveConversation.value && domainSelectionChanged.value
);

const activeDomainStatusText = computed(() => {
  if (!hasActiveConversation.value) {
    return 'Select a conversation to manage domains';
  }
  if (hasActiveDomainSelection.value) {
    const count = activeDomainSelection.value.length;
    return `${count} domain${count > 1 ? 's' : ''} selected`;
  }
  return 'All domains selected';
});

const canSend = computed(
  () => message.value.trim().length > 0 && hasActiveConversation.value
);

onMounted(async () => {
  try {
    await authStore.initialize();
  } catch (error) {
    // Initialization errors will trigger global handlers (e.g. toasts)
  }

  try {
    await chatStore.loadConversations();
  } catch (error) {
    // Error messaging handled in store
  }

  if (!domainsStore.items.length) {
    try {
      await domainsStore.loadDomains();
    } catch (error) {
      // 已在 store 内展示错误提示，这里静默处理
    }
  }
});

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick();
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  }
);

watch(
  storedDomainSelection,
  (selection) => {
    activeDomainSelection.value = normalizeDomainIds(selection);
  },
  { immediate: true }
);

watch(
  () => chatStore.activeConversationId,
  () => {
    isDomainFilterOpen.value = false;
  }
);

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

function openNewConversation() {
  isNewConversationOpen.value = true;
}

function closeNewConversation() {
  isNewConversationOpen.value = false;
  newConversationForm.name = '';
  newConversationForm.prompt = '';
  newConversationForm.domain_ids = [];
  newConversationErrors.name = '';
}

function validateNewConversation() {
  newConversationErrors.name = newConversationForm.name
    ? ''
    : 'Name is required.';
  return !newConversationErrors.name;
}

async function startConversation() {
  if (!validateNewConversation()) return;
  await chatStore.startConversation({
    name: newConversationForm.name,
    prompt: newConversationForm.prompt,
    domain_ids: newConversationForm.domain_ids
  });
  closeNewConversation();
}

async function selectConversation(id) {
  await chatStore.selectConversation(id);
}

async function sendMessage() {
  if (!canSend.value) return;
  const content = message.value.trim();
  if (!content) return;
  message.value = '';
  await chatStore.sendMessage(chatStore.activeConversationId, {
    content,
    domain_ids: activeDomainSelection.value.slice()
  });
}

function openDomainFilter() {
  if (!domainOptions.value.length) return;
  isDomainFilterOpen.value = true;
}

function toggleNewConversationDomain(domainId) {
  const id = Number(domainId);
  if (Number.isNaN(id)) return;
  const index = newConversationForm.domain_ids.indexOf(id);
  if (index === -1) {
    newConversationForm.domain_ids.push(id);
  } else {
    newConversationForm.domain_ids.splice(index, 1);
  }
}

function clearNewConversationDomains() {
  newConversationForm.domain_ids = [];
}

function toggleActiveDomain(domainId) {
  const id = Number(domainId);
  if (Number.isNaN(id)) return;
  const current = activeDomainSelection.value.slice();
  const index = current.indexOf(id);
  if (index === -1) {
    current.push(id);
  } else {
    current.splice(index, 1);
  }
  activeDomainSelection.value = normalizeDomainIds(current);
}

function clearActiveDomainSelection() {
  if (!activeDomainSelection.value.length) return;
  activeDomainSelection.value = [];
}

function applyActiveDomains() {
  if (!chatStore.activeConversationId || !domainSelectionChanged.value) {
    return;
  }
  chatStore.setConversationDomains(
    chatStore.activeConversationId,
    activeDomainSelection.value,
    { notify: true }
  );
  isDomainFilterOpen.value = false;
}

function promptRemoveConversation(id) {
  confirmingConversationId.value = id;
  isDeleteConversationOpen.value = true;
}

function closeDeleteConversation() {
  isDeleteConversationOpen.value = false;
  confirmingConversationId.value = null;
}

async function removeConversation() {
  const id = confirmingConversationId.value;
  if (!id || deletingConversationId.value) return;
  deletingConversationId.value = id;
  try {
    await chatStore.removeConversation(id);
  } finally {
    deletingConversationId.value = null;
    closeDeleteConversation();
  }
}
</script>

<style scoped>
.chat {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  height: calc(100vh - 120px);
}

.chat__sidebar {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
}

.chat__main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px 0;
}

.chat__filter-summary {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.chat__filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
}

.chat__filter-indicator {
  color: #f97316;
  font-size: 18px;
  line-height: 1;
}

.chat__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.chat__conversation-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.chat__conversation-list li {
  display: flex;
  gap: 8px;
  align-items: center;
}

.chat__conversation-trigger {
  flex: 1;
  text-align: left;
  background: #f3f4f6;
  border: none;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
}

.chat__conversation--active .chat__conversation-trigger {
  background: #1f2937;
  color: #ffffff;
}

.chat__conversation-delete {
  border: none;
  background: transparent;
  color: #ef4444;
  font-weight: 600;
  cursor: pointer;
  padding: 8px 4px;
}

.chat__conversation-delete:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.chat__conversation-name {
  font-weight: 600;
}

.chat__conversation-date {
  display: block;
  font-size: 12px;
  color: inherit;
  opacity: 0.7;
}

.chat__main {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat__domain-filter-hint {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.chat__domain-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat__domain-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f3f4f6;
  border-radius: 999px;
  font-size: 14px;
}

.chat__domain-option input {
  margin: 0;
}

.chat__domain-filter-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat__domain-filter-actions {
  display: flex;
  gap: 12px;
}

.chat__domain-filter-status {
  color: #6b7280;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat__domain-filter-dirty {
  color: #f97316;
  font-weight: 600;
}

.chat__messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat__empty {
  color: #9ca3af;
}

.chat__placeholder {
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  text-align: center;
  color: #6b7280;
}

.chat__placeholder-title {
  font-size: 20px;
  color: #374151;
}

.chat__placeholder-text {
  font-size: 15px;
  max-width: 320px;
}

.chat__message {
  padding: 16px;
  border-radius: 14px;
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat__message--user {
  align-self: flex-end;
  background: #1f2937;
  color: #ffffff;
}

.chat__message--assistant {
  align-self: flex-start;
  background: #f3f4f6;
  color: #1f2937;
}

.chat__message-meta {
  font-size: 12px;
  opacity: 0.7;
  display: flex;
  justify-content: space-between;
}

.chat__stream {
  align-self: flex-start;
  color: #6b7280;
  font-style: italic;
}

.chat__composer {
  border-top: 1px solid #e5e7eb;
  padding: 16px;
  display: flex;
  gap: 12px;
}

.chat__composer textarea {
  flex: 1;
  resize: none;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  padding: 12px;
}

.button {
  border: none;
  border-radius: 8px;
  padding: 12px 18px;
  font-weight: 600;
  cursor: pointer;
  font-size: 15px;
}

.button--primary {
  background: #1f2937;
  color: #ffffff;
}

.button--danger {
  background: #fee2e2;
  color: #b91c1c;
}
@media (max-width: 960px) {
  .chat {
    grid-template-columns: 1fr;
    height: auto;
  }

  .chat__sidebar {
    order: 2;
  }
}
</style>
