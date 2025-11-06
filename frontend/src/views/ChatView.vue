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
          <button type="button" @click="selectConversation(conversation.id)">
            <span class="chat__conversation-name">{{ conversation.name }}</span>
            <span class="chat__conversation-date">{{
              formatDate(conversation.updated_at)
            }}</span>
          </button>
        </li>
      </ul>
    </aside>

    <div class="chat__main">
      <div class="chat__messages" ref="messagesContainer">
        <p v-if="chatStore.messages.length === 0" class="chat__empty">
          Select a conversation or start a new one.
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

    <BaseModal v-model="isNewConversationOpen" title="Start New Conversation">
      <div
        class="form-field"
        :class="{ 'form-field--error': newConversationErrors.name }"
      >
        <label for="conversation-name">Conversation Name</label>
        <input
          id="conversation-name"
          v-model.trim="newConversationForm.name"
          type="text"
        />
        <p v-if="newConversationErrors.name" class="form-field__error">
          {{ newConversationErrors.name }}
        </p>
      </div>
      <div
        class="form-field"
        :class="{ 'form-field--error': newConversationErrors.prompt }"
      >
        <label for="conversation-prompt">Initial Prompt</label>
        <textarea
          id="conversation-prompt"
          v-model="newConversationForm.prompt"
          rows="4"
        ></textarea>
        <p v-if="newConversationErrors.prompt" class="form-field__error">
          {{ newConversationErrors.prompt }}
        </p>
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
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';

import BaseModal from '@/components/BaseModal.vue';
import { useChatStore } from '@/store/chat';

const chatStore = useChatStore();
const message = ref('');
const messagesContainer = ref(null);

const isNewConversationOpen = ref(false);
const newConversationForm = reactive({
  name: '',
  prompt: ''
});
const newConversationErrors = reactive({
  name: '',
  prompt: ''
});

const canSend = computed(
  () => message.value.trim().length > 0 && !!chatStore.activeConversationId
);

onMounted(async () => {
  await chatStore.loadConversations();
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
  newConversationErrors.name = '';
  newConversationErrors.prompt = '';
}

function validateNewConversation() {
  newConversationErrors.name = newConversationForm.name
    ? ''
    : 'Name is required.';
  newConversationErrors.prompt = newConversationForm.prompt
    ? ''
    : 'Initial prompt is required.';
  return !newConversationErrors.name && !newConversationErrors.prompt;
}

async function startConversation() {
  if (!validateNewConversation()) return;
  await chatStore.startConversation({
    name: newConversationForm.name,
    prompt: newConversationForm.prompt
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
  await chatStore.sendMessage(chatStore.activeConversationId, { content });
  message.value = '';
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

.chat__conversation-list button {
  width: 100%;
  text-align: left;
  background: #f3f4f6;
  border: none;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
}

.chat__conversation--active button {
  background: #1f2937;
  color: #ffffff;
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
