<template>
  <div class="chat-view">
    <ChatSidebar
      :conversations="conversations"
      :active-conversation-id="activeConversationId"
      @select="handleSelectConversation"
      @create="handleCreateConversation"
      @rename="handleRenameConversation"
      @delete="handleDeleteConversation"
      @go-home="goHome"
    />
    <div class="chat-view__main">
      <ChatWindow
        v-if="activeConversation"
        :title="activeConversation.title || '新的会话'"
        :messages="messages"
        :is-sending="isSending"
        :domains="domainOptions"
        :selected-domains="activeDomains"
        @send="handleSendMessage"
        @update:domains="updateActiveDomains"
      />
      <div v-else class="chat-view__placeholder">
        <h2>欢迎来到 Archive AI</h2>
        <p>在左侧选择或新建会话，开始与助手聊天。</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue';
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
  const title = window.prompt('请输入新的会话名称', '新的会话');
  try {
    const conversationId = await chatStore.createConversation({ title: title || '新的会话' });
    router.push({ name: 'chat', params: { conversationId } });
  } catch (error) {
    console.error('创建会话失败', error);
  }
}

async function handleRenameConversation(payload) {
  try {
    await chatStore.renameConversation(payload.id, payload.title);
  } catch (error) {
    console.error('更新会话失败', error);
  }
}

async function handleDeleteConversation(conversationId) {
  try {
    await chatStore.removeConversation(conversationId);
    if (!chatStore.activeConversationId && chatStore.conversations.length) {
      const nextId = chatStore.conversations[0].id;
      router.replace({ name: 'chat', params: { conversationId: nextId } });
    }
    if (!chatStore.conversations.length) {
      router.replace({ name: 'chat' });
    }
  } catch (error) {
    console.error('删除会话失败', error);
  }
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
</script>

<style scoped lang="scss">
.chat-view {
  display: flex;
  min-height: 100vh;
  background: #eef1fb;
}

.chat-view__main {
  flex: 1;
  min-width: 0;
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

@media (max-width: 960px) {
  .chat-view {
    flex-direction: column;
  }

  .chat-view__main {
    order: 2;
  }
}
</style>
