<template>
  <div class="chat-window">
    <header class="chat-window__header">
      <div class="chat-window__info">
        <p class="chat-window__subtitle" v-if="activeDomainNames.length">{{ selectedDomainsText }}</p>
        <p class="chat-window__subtitle" v-else>{{ texts.noDomains }}</p>
      </div>
      <div v-if="domains.length" class="chat-window__domains">
        <button type="button" class="chat-window__domains-toggle" @click="togglePanel">
          {{ domainsPanelOpen ? texts.domainToggleClose : texts.domainToggleOpen }}
        </button>
        <transition name="fade">
          <div v-if="domainsPanelOpen" class="chat-window__domains-panel">
            <p class="chat-window__domains-hint">{{ texts.domainHint }}</p>
            <div class="chat-window__domains-grid">
              <label v-for="domain in domains" :key="domain.id" class="chat-window__domains-option">
                <input
                  type="checkbox"
                  :value="domain.id"
                  :checked="pendingSelection.has(domain.id)"
                  @change="toggleDomain(domain.id)"
                />
                <span>{{ domain.name }}</span>
              </label>
            </div>
            <div class="chat-window__domains-actions">
              <button type="button" class="chat-window__domains-apply" @click="applyDomains">{{ texts.domainApply }}</button>
              <button type="button" class="chat-window__domains-clear" @click="clearDomains">{{ texts.domainClear }}</button>
            </div>
          </div>
        </transition>
      </div>
    </header>

    <main class="chat-window__messages" ref="messageContainer">
      <template v-if="messages.length">
        <article
          v-for="message in messages"
          :key="message.id"
          :class="['chat-message', `chat-message--${message.role || 'user'}`]"
        >
          <div class="chat-message__meta">
            <span class="chat-message__role">{{ renderRole(message.role) }}</span>
            <time v-if="message.created_at" class="chat-message__time">
              {{ formatTime(message.created_at) }}
            </time>
          </div>
          <div class="chat-message__content">{{ message.content }}</div>
        </article>
      </template>
      <div v-else class="chat-window__empty">
        <p>{{ texts.empty }}</p>
      </div>
      <div v-if="isSending" class="chat-window__thinking">{{ texts.thinking }}</div>
    </main>

    <form class="chat-window__composer" @submit.prevent="handleSubmit">
      <textarea
        v-model="draft"
        class="chat-window__input"
        :placeholder="texts.placeholder"
        rows="3"
        @keydown.enter.exact.prevent="handleSubmit"
        @keydown.enter.shift.stop
      ></textarea>
      <div class="chat-window__composer-actions">
        <button type="submit" class="chat-window__send" :disabled="isSending || !draft.trim()">
          {{ isSending ? texts.sending : texts.send }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isSending: {
    type: Boolean,
    default: false
  },
  domains: {
    type: Array,
    default: () => []
  },
  selectedDomains: {
    type: Array,
    default: () => []
  },
  initialDomainsOpen: {
    type: Boolean,
    default: false
  },
  texts: {
    type: Object,
    default: () => ({
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
    })
  }
});

const emit = defineEmits(['send', 'update:domains']);

const draft = ref('');
const domainsPanelOpen = ref(false);
const pendingSelection = ref(new Set(props.selectedDomains));
const messageContainer = ref(null);

watch(
  () => props.initialDomainsOpen,
  (value) => {
    if (value) {
      domainsPanelOpen.value = true;
    }
  },
  { immediate: true }
);

watch(
  () => props.selectedDomains,
  (domains) => {
    pendingSelection.value = new Set(domains);
  }
);

watch(
  () => props.messages.length,
  async () => {
    await nextTick();
    scrollToBottom();
  }
);

const activeDomainNames = computed(() => {
  if (!props.domains.length || !props.selectedDomains.length) {
    return [];
  }
  return props.domains
    .filter((domain) => props.selectedDomains.includes(domain.id))
    .map((domain) => domain.name);
});

const selectedDomainsText = computed(() => {
  const label = props.texts.selectedDomainsLabel || '';
  const joiner = props.texts.domainJoiner ?? '、';
  const names = activeDomainNames.value.join(joiner);
  return label ? `${label} ${names}` : names;
});

function togglePanel() {
  domainsPanelOpen.value = !domainsPanelOpen.value;
}

function toggleDomain(id) {
  const next = new Set(pendingSelection.value);
  const numericId = Number(id);
  if (next.has(numericId)) {
    next.delete(numericId);
  } else {
    next.add(numericId);
  }
  pendingSelection.value = next;
}

function applyDomains() {
  emit('update:domains', Array.from(pendingSelection.value));
  domainsPanelOpen.value = false;
}

function clearDomains() {
  pendingSelection.value = new Set();
  emit('update:domains', []);
}

function handleSubmit() {
  const content = draft.value.trim();
  if (!content || props.isSending) {
    return;
  }
  emit('send', {
    content,
    domain_ids: Array.from(pendingSelection.value)
  });
  draft.value = '';
}

function renderRole(role) {
  const mapping = props.texts.roles || {};
  if (role && mapping[role]) {
    return mapping[role];
  }
  return mapping.user || '我';
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return `${date.getHours().toString().padStart(2, '0')}:${date
    .getMinutes()
    .toString()
    .padStart(2, '0')}`;
}

function scrollToBottom() {
  if (!messageContainer.value) {
    return;
  }
  const element = messageContainer.value;
  element.scrollTop = element.scrollHeight;
}

onMounted(scrollToBottom);
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(180deg, #f7f8fc 0%, #ffffff 100%);
  padding: 2rem 2.5rem 2rem 4.5rem;
}

.chat-window__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid rgba(126, 139, 196, 0.25);
}

.chat-window__info {
  flex: 1;
}

.chat-window__subtitle {
  margin: 0;
  color: #6071a3;
  font-size: 0.9rem;
}

.chat-window__domains {
  position: relative;
}

.chat-window__domains-toggle {
  border: 1px solid #cdd5ff;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 999px;
  padding: 0.5rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
  color: #4a5cc8;
}

.chat-window__domains-panel {
  position: absolute;
  right: 0;
  top: 110%;
  width: 320px;
  max-height: 360px;
  overflow-y: auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 18px 40px rgba(26, 40, 90, 0.15);
  padding: 1rem 1.25rem 1.25rem;
  z-index: 10;
}

.chat-window__domains-hint {
  margin: 0 0 0.75rem;
  color: #6f7dae;
  font-size: 0.85rem;
}

.chat-window__domains-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.chat-window__domains-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.chat-window__domains-option:hover {
  background-color: rgba(74, 92, 200, 0.08);
}

.chat-window__domains-option input {
  accent-color: #4a5cc8;
}

.chat-window__domains-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.chat-window__domains-apply {
  border: none;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  font-weight: 600;
  padding: 0.45rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
}

.chat-window__domains-clear {
  border: none;
  background: none;
  color: #8a95c7;
  font-weight: 600;
  cursor: pointer;
}

.chat-window__messages {
  flex: 1;
  overflow-y: auto;
  margin: 1.5rem 0;
  padding-right: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-window__empty {
  display: grid;
  place-items: center;
  color: #7c89ba;
  height: 100%;
  text-align: center;
}

.chat-window__thinking {
  align-self: flex-start;
  padding: 0.65rem 1.1rem;
  border-radius: 12px;
  background: rgba(123, 91, 255, 0.12);
  color: #5a50b5;
  font-weight: 600;
  box-shadow: 0 12px 24px rgba(123, 91, 255, 0.15);
}

.chat-message {
  max-width: 80%;
  padding: 1rem 1.25rem;
  border-radius: 24px;
  box-shadow: 0 12px 24px rgba(29, 43, 77, 0.08);
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.chat-message--user {
  align-self: flex-end;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
}

.chat-message--assistant {
  align-self: flex-start;
  background: #ffffff;
  color: #1d2b4d;
}

.chat-message--system {
  align-self: center;
  background: rgba(255, 255, 255, 0.75);
  color: #4a5cc8;
}

.chat-message__meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  opacity: 0.75;
}

.chat-window__composer {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dfe4ff;
  border-radius: 24px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  box-shadow: 0 12px 28px rgba(26, 40, 90, 0.08);
}

.chat-window__input {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 1rem;
  font-family: inherit;
  line-height: 1.6;
  background: transparent;
}

.chat-window__composer-actions {
  display: flex;
  justify-content: flex-end;
}

.chat-window__send {
  border: none;
  border-radius: 999px;
  padding: 0.6rem 1.6rem;
  font-weight: 600;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.chat-window__send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.25);
}

.chat-window__send:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
