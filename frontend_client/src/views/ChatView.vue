<template>
  <div class="chat-view" :class="{ 'chat-view--collapsed': isSidebarCollapsed }">
    <ChatSidebar
      v-if="!isSidebarCollapsed"
      :conversations="conversations"
      :active-conversation-id="activeConversationId"
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
        aria-label="折叠会话历史侧边栏"
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
        <span class="chat-view__sr-only">折叠会话历史侧边栏</span>
      </button>
      <button
        v-if="isSidebarCollapsed"
        type="button"
        class="chat-view__sidebar-expand"
        @click="expandSidebar"
        aria-label="展开会话历史侧边栏"
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
        <span class="chat-view__sr-only">展开会话历史侧边栏</span>
      </button>
      <ChatWindow
        v-if="activeConversation"
        :messages="messages"
        :is-sending="isSending"
        :domains="domainOptions"
        :selected-domains="activeDomains"
        @send="handleSendMessage"
        @update:domains="updateActiveDomains"
      />
      <div v-else class="chat-view__placeholder">
        <div class="chat-view__welcome">
          <h2>欢迎使用档案库 AI 助手</h2>
          <p>在左侧选择会话，或在下方输入问题开始对话。</p>
          <form class="chat-view__search" @submit.prevent="handlePlaceholderSubmit">
            <input
              v-model="placeholderQuery"
              class="chat-view__search-input"
              type="text"
              placeholder="请输入问题，按下回车或点击发送"
            />
            <button
              type="submit"
              class="chat-view__search-button"
              :disabled="isPlaceholderSubmitting || !placeholderQuery.trim()"
            >
              {{ isPlaceholderSubmitting ? '创建中…' : '开始对话' }}
            </button>
          </form>
        </div>
      </div>
    </div>

    <transition name="chat-dialog-fade">
      <div v-if="showRenameDialog" class="chat-dialog-overlay">
        <div class="chat-dialog" role="dialog" aria-modal="true" aria-labelledby="rename-dialog-title">
          <h3 id="rename-dialog-title" class="chat-dialog__title">重命名会话</h3>
          <form class="chat-dialog__form" @submit.prevent="submitRenameDialog">
            <label class="chat-dialog__label">
              新的名称
              <input
                v-model="renameTitle"
                class="chat-dialog__input"
                type="text"
                placeholder="请输入新的会话名称"
                :disabled="isRenamingConversation"
              />
            </label>
            <div class="chat-dialog__actions">
              <button type="button" class="chat-dialog__button" @click="closeRenameDialog" :disabled="isRenamingConversation">
                取消
              </button>
              <button type="submit" class="chat-dialog__button chat-dialog__button--primary" :disabled="isRenamingConversation">
                {{ isRenamingConversation ? '保存中…' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <transition name="chat-dialog-fade">
      <div v-if="showDeleteDialog" class="chat-dialog-overlay">
        <div class="chat-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
          <h3 id="delete-dialog-title" class="chat-dialog__title">删除会话</h3>
          <p class="chat-dialog__message">
            确定要删除 “{{ deleteTarget?.title || '未命名会话' }}” 吗？该操作不可撤销。
          </p>
          <div class="chat-dialog__actions">
            <button type="button" class="chat-dialog__button" @click="closeDeleteDialog" :disabled="isDeletingConversation">
              取消
            </button>
            <button
              type="button"
              class="chat-dialog__button chat-dialog__button--danger"
              @click="confirmDeleteDialog"
              :disabled="isDeletingConversation"
            >
              {{ isDeletingConversation ? '删除中…' : '删除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ChatSidebar from '@/components/ChatSidebar.vue';
import ChatWindow from '@/components/ChatWindow.vue';
import { useChatStore } from '@/store/chat';
import { useDomainsStore } from '@/store/domains';

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const domainsStore = useDomainsStore();

const conversations = computed(() => chatStore.conversations);
const activeConversation = computed(() => chatStore.activeConversation);
const messages = computed(() => chatStore.messages);
const isSending = computed(() => chatStore.isSending);
const activeConversationId = computed(() => chatStore.activeConversationId);
const domainOptions = computed(() => domainsStore.items);
const activeDomains = computed(() => chatStore.getConversationDomains(chatStore.activeConversationId));

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

onMounted(async () => {
  await domainsStore.loadDomains();
  await chatStore.loadConversations();
  await syncFromRoute({ fallbackToFirst: true });
});

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

async function handlePlaceholderSubmit() {
  const content = placeholderQuery.value.trim();
  if (!content || isPlaceholderSubmitting.value) {
    return;
  }
  isPlaceholderSubmitting.value = true;
  try {
    const conversationId = await chatStore.createConversation({
      title: content.slice(0, 30),
      initialMessage: content
    });
    placeholderQuery.value = '';
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
  border: 1px solid #d9e1ff;
  background: rgba(255, 255, 255, 0.9);
  color: #4b5d96;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.15);
  transition: background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
  z-index: 10;
}
.chat-view__sidebar-collapse:hover,
.chat-view__sidebar-expand:hover {
  background-color: #eef1fb;
  color: #1f2a56;
  box-shadow: 0 16px 30px rgba(72, 102, 255, 0.22);
}

.chat-view__sidebar-collapse-icon {
  width: 20px;
  height: 20px;
}

.chat-view__sidebar-expand-icon {
  width: 20px;
  height: 20px;
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
  height: 100vh;
  display: grid;
  place-items: center;
  text-align: center;
  color: #5d6aa2;
}

.chat-view__placeholder h2 {
  margin-bottom: 0.75rem;
  font-size: 1.6rem;
  color: #1f2a56;
}

.chat-view__welcome {
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 2rem;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.75);
  box-shadow: 0 20px 40px rgba(102, 120, 255, 0.12);
}

.chat-view__welcome p {
  margin: 0;
  color: #5a6b97;
  line-height: 1.6;
}

.chat-view__search {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-view__search-input {
  width: 100%;
  padding: 0.8rem 1rem;
  border-radius: 14px;
  border: 1px solid #d5dbff;
  background: rgba(255, 255, 255, 0.9);
  font-size: 1rem;
  box-shadow: inset 0 1px 2px rgba(31, 42, 86, 0.05);
}

.chat-view__search-input:focus {
  outline: none;
  border-color: #7b5bff;
  box-shadow: 0 0 0 4px rgba(123, 91, 255, 0.15);
}

.chat-view__search-button {
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.chat-view__search-button:disabled {
  cursor: not-allowed;
  opacity: 0.75;
  box-shadow: none;
}

.chat-view__search-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(72, 102, 255, 0.25);
}

.chat-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 1.5rem;
}

.chat-dialog {
  width: min(420px, 100%);
  background: #fff;
  border-radius: 20px;
  padding: 1.75rem;
  box-shadow: 0 20px 40px rgba(31, 42, 86, 0.18);
}

.chat-dialog__title {
  margin: 0 0 1rem;
  font-size: 1.25rem;
  color: #1f2a56;
  font-weight: 700;
}

.chat-dialog__form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-dialog__label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: #4a5cc8;
  font-weight: 600;
  font-size: 0.95rem;
}

.chat-dialog__input {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  border: 1px solid #d5dbff;
  font-size: 1rem;
}

.chat-dialog__input:focus {
  outline: none;
  border-color: #7b5bff;
  box-shadow: 0 0 0 4px rgba(123, 91, 255, 0.15);
}

.chat-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.chat-dialog__button {
  min-width: 96px;
  padding: 0.6rem 1rem;
  border-radius: 10px;
  border: 1px solid #d5dbff;
  background: #fff;
  color: #4a5cc8;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.chat-dialog__button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.chat-dialog__button--primary {
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  border-color: transparent;
  color: #fff;
}

.chat-dialog__button--danger {
  background: #fef2f4;
  border-color: #f9cfd6;
  color: #cf3c4f;
}

.chat-dialog__message {
  margin: 0 0 1.5rem;
  color: #5d6aa2;
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
  .chat-view {
    flex-direction: column;
  }

  .chat-view__main {
    order: 2;
  }
}
</style>
