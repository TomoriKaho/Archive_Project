<template>
  <div class="chat-view" :class="{ 'chat-view--collapsed': isSidebarCollapsed }">
    <ChatSidebar
      v-if="!isSidebarCollapsed"
      :conversations="conversations"
      :active-conversation-id="activeConversationId"
      :texts="texts.sidebar"
      @select="handleSelectConversation"
      @create="handleCreateConversation"
      @rename="handleRenameConversation"
      @delete="handleDeleteConversation"
      @go-home="goHome"
    />
    <div class="chat-view__main">
      <button
        v-if="!isSidebarCollapsed"
        type="button"
        class="chat-view__sidebar-collapse"
        @click="collapseSidebar"
        :aria-label="texts.collapseSidebarAria"
      >
        <svg class="chat-view__sidebar-collapse-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path
            d="M10.5 6.75l-4.5 5.25 4.5 5.25M18 5.25v13.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span class="chat-view__sr-only">{{ texts.collapseSidebarSr }}</span>
      </button>
      <button
        v-if="isSidebarCollapsed"
        type="button"
        class="chat-view__sidebar-expand"
        @click="expandSidebar"
        :aria-label="texts.expandSidebarAria"
      >
        <svg class="chat-view__sidebar-expand-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path
            d="M13.5 6.75l4.5 5.25-4.5 5.25M6 5.25v13.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span class="chat-view__sr-only">{{ texts.expandSidebarSr }}</span>
      </button>
      <ChatWindow
        v-if="activeConversation"
        :messages="messages"
        :is-sending="isSending"
        :domains="domainOptions"
        :selected-domains="activeDomains"
        :initial-domains-open="shouldOpenDomains"
        :texts="texts.chatWindow"
        @send="handleSendMessage"
        @update:domains="updateActiveDomains"
      />
      <div v-else class="chat-view__placeholder">
        <div class="chat-view__welcome">
          <h2>{{ texts.placeholder.title }}</h2>
          <p>{{ texts.placeholder.subtitle }}</p>
          <QueryComposer
            v-model="placeholderQuery"
            :texts="texts.placeholder.composer"
            :domains="domainOptions"
            :selected-domains="selectedDomains"
            :submitting="isPlaceholderSubmitting"
            @submit="handlePlaceholderSubmit"
            @update:domains="updatePreferredDomains"
          />
        </div>
      </div>
    </div>

    <transition name="chat-dialog-fade">
      <div v-if="showRenameDialog" class="chat-dialog-overlay">
        <div class="chat-dialog" role="dialog" aria-modal="true" :aria-labelledby="renameDialogId">
          <h3 :id="renameDialogId" class="chat-dialog__title">{{ texts.renameDialog.title }}</h3>
          <form class="chat-dialog__form" @submit.prevent="submitRenameDialog">
            <label class="chat-dialog__label">
              {{ texts.renameDialog.label }}
              <input
                v-model="renameTitle"
                class="chat-dialog__input"
                type="text"
                :placeholder="texts.renameDialog.placeholder"
                :disabled="isRenamingConversation"
              />
            </label>
            <div class="chat-dialog__actions">
              <button type="button" class="chat-dialog__button" @click="closeRenameDialog" :disabled="isRenamingConversation">
                {{ texts.renameDialog.cancel }}
              </button>
              <button type="submit" class="chat-dialog__button chat-dialog__button--primary" :disabled="isRenamingConversation">
                {{ isRenamingConversation ? texts.renameDialog.saving : texts.renameDialog.save }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <transition name="chat-dialog-fade">
      <div v-if="showDeleteDialog" class="chat-dialog-overlay">
        <div class="chat-dialog" role="dialog" aria-modal="true" :aria-labelledby="deleteDialogId">
          <h3 :id="deleteDialogId" class="chat-dialog__title">{{ texts.deleteDialog.title }}</h3>
          <p class="chat-dialog__message">
            {{ texts.deleteDialog.message(deleteTarget?.title) }}
          </p>
          <div class="chat-dialog__actions">
            <button type="button" class="chat-dialog__button" @click="closeDeleteDialog" :disabled="isDeletingConversation">
              {{ texts.deleteDialog.cancel }}
            </button>
            <button
              type="button"
              class="chat-dialog__button chat-dialog__button--danger"
              @click="confirmDeleteDialog"
              :disabled="isDeletingConversation"
            >
              {{ isDeletingConversation ? texts.deleteDialog.confirming : texts.deleteDialog.confirm }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ChatSidebar from '@/components/ChatSidebar.vue';
import ChatWindow from '@/components/ChatWindow.vue';
import QueryComposer from '@/components/QueryComposer.vue';
import { useChatStore } from '@/store/chat';
import { useDomainsStore } from '@/store/domains';
import { usePreferencesStore } from '@/store/preferences';

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const domainsStore = useDomainsStore();
const preferencesStore = usePreferencesStore();

const conversations = computed(() => chatStore.conversations);
const activeConversation = computed(() => chatStore.activeConversation);
const messages = computed(() => chatStore.messages);
const isSending = computed(() => chatStore.isSending);
const activeConversationId = computed(() => chatStore.activeConversationId);
const domainOptions = computed(() => domainsStore.items);
const activeDomains = computed(() => chatStore.getConversationDomains(chatStore.activeConversationId));
const selectedDomains = computed(() => preferencesStore.preferredDomainIds);

const language = computed(() => preferencesStore.language);

const languagePack = {
  zh: {
    collapseSidebarAria: '折叠会话历史侧边栏',
    collapseSidebarSr: '折叠会话历史侧边栏',
    expandSidebarAria: '展开会话历史侧边栏',
    expandSidebarSr: '展开会话历史侧边栏',
    placeholder: {
      title: '欢迎使用档案库 AI 助手',
      subtitle: '在左侧选择会话，或在下方输入问题开始对话。',
      composer: {
        placeholder: '请输入问题，例如：张小明是谁？',
        submit: '开始对话',
        submitting: '创建中…',
        domainButton: '选择知识域',
        domainBadge: (count) => `已选${count}`,
        domainHint: '选择后发送消息时仅检索勾选的知识域，不勾选默认从全部知识域检索。',
        domainApply: '应用',
        domainClear: '清除'
      }
    },
    renameDialog: {
      title: '重命名会话',
      label: '新的名称',
      placeholder: '请输入新的会话名称',
      cancel: '取消',
      save: '保存',
      saving: '保存中…'
    },
    deleteDialog: {
      title: '删除会话',
      message: (title) => `确定要删除会话 “${title || '未命名会话'}” 吗？该操作不可撤销。`,
      cancel: '取消',
      confirm: '删除',
      confirming: '删除中…'
    },
    sidebar: {
      title: '会话历史',
      subtitle: '管理你的提问与回答',
      create: '新建',
      rename: '重命名',
      delete: '删除',
      empty: '还没有会话，点击“新建”开始提问。',
      goHome: '返回主页'
    },
    chatWindow: {
      selectedDomainsLabel: '已选择知识域：',
      noDomains: '未限定知识域，将在全部知识库中检索。',
      domainToggleOpen: '选择知识域',
      domainToggleClose: '收起知识域',
      domainHint: '选择后发送消息时仅检索勾选的知识域，不勾选默认从全部知识域检索。',
      domainApply: '应用',
      domainClear: '清除',
      empty: '开始新的对话，系统将基于选定的知识域为你解答。',
      thinking: '助手正在思考…',
      placeholder: '输入问题，Shift+Enter 换行',
      send: '发送',
      sending: '发送中…',
      domainJoiner: '、',
      roles: {
        user: '我',
        assistant: '助手',
        system: '系统'
      }
    }
  },
  en: {
    collapseSidebarAria: 'Collapse conversation history sidebar',
    collapseSidebarSr: 'Collapse conversation history sidebar',
    expandSidebarAria: 'Expand conversation history sidebar',
    expandSidebarSr: 'Expand conversation history sidebar',
    placeholder: {
      title: 'Welcome to the Archives AI Assistant',
      subtitle: 'Pick a conversation on the left or start a new one below.',
      composer: {
        placeholder: 'Ask something, e.g. Who is Zhang Xiaoming?',
        submit: 'Start chatting',
        submitting: 'Creating…',
        domainButton: 'Choose Domains',
        domainBadge: (count) => `${count} selected`,
        domainHint:
          'When selected, messages will only search the checked domains. Leave unchecked to search all domains.',
        domainApply: 'Apply',
        domainClear: 'Clear'
      }
    },
    renameDialog: {
      title: 'Rename conversation',
      label: 'New name',
      placeholder: 'Enter a new conversation name',
      cancel: 'Cancel',
      save: 'Save',
      saving: 'Saving…'
    },
    deleteDialog: {
      title: 'Delete conversation',
      message: (title) => `Are you sure you want to delete “${title || 'Untitled conversation'}”? This action cannot be undone.`,
      cancel: 'Cancel',
      confirm: 'Delete',
      confirming: 'Deleting…'
    },
    sidebar: {
      title: 'History',
      subtitle: 'Manage your questions and answers',
      create: 'New',
      rename: 'Rename',
      delete: 'Delete',
      empty: 'No conversations yet.\nClick “New” to start.',
      goHome: 'Back to home'
    },
    chatWindow: {
      selectedDomainsLabel: 'Selected domains:',
      noDomains: 'No domain filter. Searching the entire knowledge base.',
      domainToggleOpen: 'Choose domains',
      domainToggleClose: 'Hide domains',
      domainHint:
        'When selected, messages will only search the checked domains. Leave unchecked to search all domains.',
      domainApply: 'Apply',
      domainClear: 'Clear',
      empty: 'Start a new conversation and the assistant will answer based on the selected domains.',
      thinking: 'Assistant is thinking…',
      placeholder: 'Type your question. Shift+Enter for a new line.',
      send: 'Send',
      sending: 'Sending…',
      domainJoiner: ', ',
      roles: {
        user: 'Me',
        assistant: 'Assistant',
        system: 'System'
      }
    }
  }
};

const texts = computed(() => languagePack[language.value]);

const showRenameDialog = ref(false);
const renameTarget = ref(null);
const renameTitle = ref('');
const isRenamingConversation = ref(false);

const showDeleteDialog = ref(false);
const deleteTarget = ref(null);
const isDeletingConversation = ref(false);

const placeholderQuery = ref('');
const isPlaceholderSubmitting = ref(false);
const isSidebarCollapsed = ref(false);
const shouldOpenDomains = ref(false);

const renameDialogId = 'chat-rename-dialog';
const deleteDialogId = 'chat-delete-dialog';

onMounted(async () => {
  await domainsStore.loadDomains();
  await chatStore.loadConversations();
  await syncFromRoute({ fallbackToFirst: true });
});

watch(
  () => route.query.openDomains,
  (value) => {
    if (value == null) {
      return;
    }
    shouldOpenDomains.value = true;
    const rest = { ...route.query };
    delete rest.openDomains;
    router.replace({ name: route.name || 'chat', params: { ...route.params }, query: rest });
  },
  { immediate: true }
);

watch(
  [shouldOpenDomains, activeConversation],
  ([open, conversation]) => {
    if (open && conversation) {
      nextTick(() => {
        shouldOpenDomains.value = false;
      });
    }
  }
);

watch(
  () => route.params.conversationId,
  async () => {
    await syncFromRoute({ fallbackToFirst: false });
  }
);

watch(
  () => chatStore.activeConversationId,
  (conversationId) => {
    const paramId = Number(route.params.conversationId);
    if (conversationId && conversationId !== paramId) {
      router.replace({ name: 'chat', params: { conversationId } });
    }
  }
);

watch(
  language,
  (value) => {
    const locale = value === 'zh' ? 'zh-CN' : 'en-US';
    document.documentElement.setAttribute('lang', locale);
  },
  { immediate: true }
);

async function syncFromRoute({ fallbackToFirst }) {
  const param = route.params.conversationId;
  const numericId = Number(param);
  if (param && Number.isFinite(numericId)) {
    const exists = conversations.value.some((item) => item.id === numericId);
    if (!exists) {
      await chatStore.loadConversations();
    }
    const refreshed = conversations.value.some((item) => item.id === numericId);
    if (refreshed) {
      await chatStore.selectConversation(numericId);
      return;
    }
  }
  if (fallbackToFirst && conversations.value.length) {
    const firstId = conversations.value[0].id;
    await chatStore.selectConversation(firstId);
    router.replace({ name: 'chat', params: { conversationId: firstId } });
  } else if (!conversations.value.length) {
    await chatStore.selectConversation(null);
  }
}

async function handleSelectConversation(conversationId) {
  await chatStore.selectConversation(conversationId);
}

async function handleCreateConversation() {
  preferencesStore.setPreferredDomainIds([]);
  placeholderQuery.value = '';
  await chatStore.selectConversation(null);
  if (route.name !== 'chat' || route.params.conversationId) {
    router.push({ name: 'chat' });
  }
}

function handleRenameConversation(conversation) {
  if (!conversation) {
    return;
  }
  renameTarget.value = conversation;
  renameTitle.value = conversation.title || '';
  showRenameDialog.value = true;
}

function handleDeleteConversation(conversation) {
  if (!conversation) {
    return;
  }
  deleteTarget.value = conversation;
  showDeleteDialog.value = true;
}

async function handleSendMessage(payload) {
  if (!chatStore.activeConversationId) {
    return;
  }
  try {
    await chatStore.sendMessage(chatStore.activeConversationId, payload);
  } catch (error) {
    console.error('发送消息失败', error);
  }
}

function updateActiveDomains(domainIds) {
  if (!chatStore.activeConversationId) {
    return;
  }
  chatStore.setConversationDomains(chatStore.activeConversationId, domainIds);
}

function updatePreferredDomains(domainIds) {
  preferencesStore.setPreferredDomainIds(domainIds);
}

function goHome() {
  router.push({ name: 'landing' });
}

async function submitRenameDialog() {
  if (!renameTarget.value || isRenamingConversation.value) {
    return;
  }
  isRenamingConversation.value = true;
  try {
    await chatStore.renameConversation(renameTarget.value.id, renameTitle.value);
    showRenameDialog.value = false;
    renameTarget.value = null;
    renameTitle.value = '';
  } catch (error) {
    console.error('更新会话失败', error);
  } finally {
    isRenamingConversation.value = false;
  }
}

function closeRenameDialog() {
  showRenameDialog.value = false;
  renameTarget.value = null;
  renameTitle.value = '';
}

async function confirmDeleteDialog() {
  if (!deleteTarget.value || isDeletingConversation.value) {
    return;
  }
  isDeletingConversation.value = true;
  const targetId = deleteTarget.value.id;
  try {
    await chatStore.removeConversation(targetId);
    if (!chatStore.activeConversationId && chatStore.conversations.length) {
      const nextId = chatStore.conversations[0].id;
      router.replace({ name: 'chat', params: { conversationId: nextId } });
    }
    if (!chatStore.conversations.length) {
      router.replace({ name: 'chat' });
    }
    showDeleteDialog.value = false;
    deleteTarget.value = null;
  } catch (error) {
    console.error('删除会话失败', error);
  } finally {
    isDeletingConversation.value = false;
  }
}

function closeDeleteDialog() {
  showDeleteDialog.value = false;
  deleteTarget.value = null;
}

function collapseSidebar() {
  isSidebarCollapsed.value = true;
}

function expandSidebar() {
  isSidebarCollapsed.value = false;
}

async function handlePlaceholderSubmit(value) {
  const content = value.trim();
  if (!content || isPlaceholderSubmitting.value) {
    return;
  }
  isPlaceholderSubmitting.value = true;
  try {
    const conversationId = await chatStore.createConversation({
      title: content.slice(0, 30),
      initialMessage: content,
      domainIds: selectedDomains.value
    });
    placeholderQuery.value = '';
    preferencesStore.setPreferredDomainIds([]);
    router.push({ name: 'chat', params: { conversationId } });
  } catch (error) {
    console.error('创建会话失败', error);
  } finally {
    isPlaceholderSubmitting.value = false;
  }
}
</script>

<style scoped lang="scss">
.chat-view {
  display: flex;
  min-height: 100vh;
  background: #eef1fb;
}

.chat-view__main {
  position: relative;
  flex: 1;
  min-width: 0;
}

.chat-view__sidebar-collapse,
.chat-view__sidebar-expand {
  position: absolute;
  top: 1.5rem;
  left: 1.5rem;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  color: #4a5cc8;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(74, 92, 200, 0.18);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  z-index: 5;
}

.chat-view__sidebar-collapse:hover,
.chat-view__sidebar-expand:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 32px rgba(74, 92, 200, 0.25);
}

.chat-view__sidebar-collapse-icon,
.chat-view__sidebar-expand-icon {
  width: 24px;
  height: 24px;
}

.chat-view__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.chat-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  padding: 4rem 1.5rem;
}

.chat-view__welcome {
  width: min(640px, 100%);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  padding: 3rem 2.5rem;
  text-align: center;
  box-shadow: 0 24px 48px rgba(18, 43, 90, 0.12);
}

.chat-view__welcome h2 {
  margin-bottom: 0.75rem;
  font-size: 2rem;
  color: #1d2b4d;
}

.chat-view__welcome p {
  margin-bottom: 2rem;
  color: #5a6b97;
}

.chat-view--collapsed .chat-sidebar {
  display: none;
}

.chat-view--collapsed .chat-view__sidebar-expand {
  left: 1.5rem;
}

.chat-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 17, 51, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.chat-dialog {
  background: #fff;
  border-radius: 20px;
  padding: 2rem;
  width: min(420px, 90%);
  box-shadow: 0 24px 48px rgba(17, 30, 75, 0.2);
}

.chat-dialog__title {
  margin: 0 0 1.25rem;
  font-size: 1.35rem;
  color: #1f2a56;
}

.chat-dialog__form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chat-dialog__label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: #4a5cc8;
}

.chat-dialog__input {
  border: 1px solid #dfe4ff;
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  font-size: 1rem;
  outline: none;
}

.chat-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.chat-dialog__button {
  border: none;
  border-radius: 10px;
  padding: 0.5rem 1.2rem;
  font-weight: 600;
  cursor: pointer;
}

.chat-dialog__button--primary {
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
}

.chat-dialog__button--danger {
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
  color: #fff;
}

.chat-dialog__message {
  margin: 0 0 1.25rem;
  color: #5a6b97;
  line-height: 1.6;
}

.chat-dialog-fade-enter-active,
.chat-dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.chat-dialog-fade-enter-from,
.chat-dialog-fade-leave-to {
  opacity: 0;
}

@media (max-width: 960px) {
  .chat-view__sidebar-collapse,
  .chat-view__sidebar-expand {
    top: 1rem;
    left: 1rem;
  }

  .chat-view__welcome {
    padding: 2.5rem 1.75rem;
  }
}

@media (max-width: 720px) {
  .chat-view__welcome h2 {
    font-size: 1.75rem;
  }

  .chat-view__welcome {
    padding: 2.25rem 1.5rem;
  }
}
</style>
