<template>
  <div class="chat-window">

    <div class="chat-window__topbar">
      <div class="chat-window__top-actions">
        <button type="button" class="chat-window__top-button" @click="emit('toggle-language')">
          <span class="chat-window__top-flag" aria-hidden="true">{{ texts.languageFlag }}</span>
          <span>{{ texts.languageLabel }}</span>
        </button>
        <button type="button" class="chat-window__top-button chat-window__top-button--danger" @click="emit('delete-conversation')">
          {{ texts.deleteConversation }}
        </button>
      </div>
    </div>

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
          <div class="chat-message__content" v-html="renderContent(message)"></div>
        </article>
      </template>
      <div v-else class="chat-window__empty">
        <p>{{ texts.empty }}</p>
      </div>
      <transition name="chat-status" mode="out-in">
        <div v-if="isThinkingDisplayed" key="thinking" class="chat-window__streaming chat-window__streaming--thinking">
          <span class="chat-window__streaming-label chat-window__streaming-label--pulse">{{ texts.thinking }}</span>
          <div class="chat-window__progress" aria-hidden="true">
            <div class="chat-window__progress-bar" :style="{ width: `${thinkingProgress}%` }"></div>
          </div>
          <button type="button" class="chat-window__stop" @click="emit('stop-thinking')">
            {{ texts.stopThinking || texts.stop }}
          </button>
        </div>
        <div v-else-if="canRestart" key="stopped" class="chat-window__streaming chat-window__streaming--stopped">
          <span class="chat-window__streaming-label">{{ texts.stopped }}</span>
          <button type="button" class="chat-window__stop chat-window__stop--restart" @click="emit('restart-thinking')">
            {{ texts.restart }}
          </button>
        </div>
        <div v-else-if="isStreaming" key="streaming" class="chat-window__streaming">
          <span class="chat-window__streaming-label">{{ texts.streaming }}</span>
          <button type="button" class="chat-window__stop" @click="emit('stop-stream')">
            {{ texts.stop }}
          </button>
        </div>
        <div v-else-if="isStreamPaused" key="paused" class="chat-window__streaming chat-window__streaming--paused">
          <span class="chat-window__streaming-label">{{ texts.paused }}</span>
          <button type="button" class="chat-window__stop" @click="emit('resume-stream')">
            {{ texts.resume }}
          </button>
        </div>
      </transition>
    </main>

    <form class="chat-window__composer" @submit.prevent="handleSubmit">
      <textarea
        ref="composerInput"
        v-model="draft"
        class="chat-window__input"
        :placeholder="texts.placeholder"
        rows="1"
        @input="autoResizeInput"
        @keydown.enter.exact.prevent="handleSubmit"
        @keydown.enter.shift.stop
      ></textarea>
      <div class="chat-window__composer-actions">
        <div v-if="domains.length" class="chat-window__domains">
          <button type="button" class="chat-window__domains-toggle" @click="togglePanel">
            <span class="chat-window__domains-icon" aria-hidden="true">＋</span>
            <span>{{ texts.domainToggleOpen }}</span>
            <span v-if="selectedDomainsCount" class="chat-window__domains-badge">{{ domainBadge }}</span>
            <span class="chat-window__domains-caret" aria-hidden="true">▴</span>
          </button>
          <transition name="fade">
            <div
              v-if="domainsPanelOpen"
              class="chat-window__domains-panel"
              :class="{ 'chat-window__domains-panel--scrollable': shouldScrollDomains }"
            >
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
        <button type="submit" class="chat-window__send" :disabled="isSending || !draft.trim()">
          {{ isSending ? texts.sending : texts.send }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isSending: {
    type: Boolean,
    default: false
  },
  assistantPhase: {
    type: String,
    default: null
  },
  isStreaming: {
    type: Boolean,
    default: false
  },
  isStreamPaused: {
    type: Boolean,
    default: false
  },
  canRestart: {
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
      domainBadge: (count) => `已选${count}`,
      domainHint: '选择后仅检索勾选的知识域，                不勾选默认从全部知识域检索。',
      domainApply: '应用',
      domainClear: '清除',
      languageToggle: '切换语言',
      languageLabel: '中文',
      languageFlag: '🇨🇳',
      deleteConversation: '删除会话',
      empty: '开始新的对话，系统将基于选定的知识域为你解答。',
      retrieving: '助手正在思考…',
      thinking: '助手正在思考…',
      stopThinking: '停止思考',
      stopped: '已停止思考',
      restart: '重新思考',
      streaming: '助手正在回复…',
      paused: '已暂停思考',
      resume: '重新思考输出',
      stop: '停止输出',
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

const emit = defineEmits([
  'send',
  'update:domains',
  'stop-stream',
  'resume-stream',
  'stop-thinking',
  'restart-thinking',
  'toggle-language',
  'delete-conversation'
]);

const draft = ref('');
const composerInput = ref(null);
const domainsPanelOpen = ref(false);
const pendingSelection = ref(new Set(props.selectedDomains));
const messageContainer = ref(null);
const currentPhase = computed(() => props.assistantPhase || (props.isSending ? 'thinking' : null));
const isRetrieving = computed(() => currentPhase.value === 'retrieving');
const isThinking = computed(() => currentPhase.value === 'thinking');
const isThinkingPhase = computed(() => isRetrieving.value || isThinking.value);
const thinkingCompletionPending = ref(false);
const isThinkingDisplayed = computed(() => isThinkingPhase.value || thinkingCompletionPending.value);
const thinkingProgress = ref(0);
let progressTimer = null;
let completionResetTimer = null;

function clearProgressTimer() {
  if (progressTimer) {
    clearTimeout(progressTimer);
    progressTimer = null;
  }
}

function clearCompletionResetTimer() {
  if (completionResetTimer) {
    clearTimeout(completionResetTimer);
    completionResetTimer = null;
  }
}

function holdCompletion(duration) {
  clearCompletionResetTimer();
  thinkingCompletionPending.value = true;
  completionResetTimer = window.setTimeout(() => {
    thinkingCompletionPending.value = false;
    thinkingProgress.value = 0;
    completionResetTimer = null;
  }, duration);
}

function scheduleProgress() {
  clearProgressTimer();

  if (!isThinkingPhase.value) {
    return;
  }

  const milestones = [60, 80, 92];
  const current = thinkingProgress.value;
  const stageIndex = milestones.findIndex((target) => current < target);
  const nextTarget = stageIndex === -1 ? 96 : milestones[stageIndex];
  const step = Math.max(1, Math.round((nextTarget - current) / 8));
  const delay = 300 + Math.max(0, stageIndex) * 280;

  thinkingProgress.value = Math.min(nextTarget, current + step);
  progressTimer = window.setTimeout(scheduleProgress, delay);
}

watch(isThinkingPhase, (active, wasActive) => {
  if (active) {
    clearCompletionResetTimer();
    thinkingCompletionPending.value = false;
    thinkingProgress.value = 0;
    scheduleProgress();
    return;
  }

  clearProgressTimer();
  if (wasActive) {
    thinkingProgress.value = 100;
    holdCompletion(props.isStreaming ? 260 : 700);
  } else {
    thinkingProgress.value = 0;
  }
});

watch(
  () => props.isStreaming,
  (streaming) => {
    if (streaming && isThinkingDisplayed.value) {
      clearProgressTimer();
      thinkingProgress.value = 100;
      holdCompletion(260);
    }
  }
);

const MIN_INPUT_HEIGHT = 44;
const MAX_INPUT_HEIGHT = 240;

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

watch(
  () => props.messages.map((message) => `${message.id}-${message.content?.length ?? 0}`).join('|'),
  async () => {
    await nextTick();
    scrollToBottom();
  }
);

watch(
  draft,
  () => {
    nextTick(autoResizeInput);
  }
);

const shouldScrollDomains = computed(() => props.domains.length > 2);
const selectedDomainsCount = computed(() => pendingSelection.value.size);

const domainBadge = computed(() => {
  const count = selectedDomainsCount.value;
  if (!count) {
    return '';
  }
  const badge = props.texts?.domainBadge;
  if (typeof badge === 'function') {
    return badge(count);
  }
  if (typeof badge === 'string') {
    return badge.replace('{count}', count);
  }
  return count.toString();
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
  nextTick(autoResizeInput);
}

function renderRole(role) {
  const mapping = props.texts.roles || {};
  if (role && mapping[role]) {
    return mapping[role];
  }
  return mapping.user || '我';
}

function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function linkifyContent(text) {
  if (!text) {
    return '';
  }

  const pattern = /(https?:\/\/[^\s<>"']+)/gi;
  let result = '';
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const [url] = match;
    const start = match.index ?? 0;
    result += escapeHtml(text.slice(lastIndex, start));
    const { coreUrl, trailing } = splitUrl(url);
    if (!coreUrl) {
      result += escapeHtml(url);
      lastIndex = start + url.length;
      continue;
    }
    const safeUrl = escapeHtml(coreUrl);
    result += `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`;
    result += escapeHtml(trailing);
    lastIndex = start + url.length;
  }

  result += escapeHtml(text.slice(lastIndex));
  return result;
}

function splitUrl(url) {
  const urlChar = /[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]/;
  const trailingMarks = /[.,!?;:，。！？；：)\]]/u;
  let end = url.length;

  while (end > 0) {
    const char = url[end - 1];
    const isMarkdownMarker = char === '*' || char === '_' || char === '`';
    const isInvalidChar = !urlChar.test(char);
    if (isMarkdownMarker || trailingMarks.test(char) || isInvalidChar) {
      end -= 1;
      continue;
    }
    break;
  }

  return {
    coreUrl: url.slice(0, end),
    trailing: url.slice(end)
  };
}

function renderContent(message) {
  const content = message?.content ?? '';
  if (message?.role === 'assistant') {
    return applyLineBreaks(linkifyContent(String(content)));
  }
  return applyLineBreaks(escapeHtml(String(content)));
}

function applyLineBreaks(html) {
  return String(html).replaceAll('\n', '<br />');
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}/${month}/${day} ${hours}:${minutes}`;
}

function scrollToBottom() {
  if (!messageContainer.value) {
    return;
  }
  const element = messageContainer.value;
  element.scrollTop = element.scrollHeight;
}

onMounted(() => {
  scrollToBottom();
  autoResizeInput();
});

onBeforeUnmount(() => {
  clearProgressTimer();
});

function autoResizeInput() {
  const input = composerInput.value;
  if (!input) {
    return;
  }
  input.style.height = 'auto';
  const nextHeight = Math.min(input.scrollHeight, MAX_INPUT_HEIGHT);
  const clamped = Math.max(MIN_INPUT_HEIGHT, nextHeight);
  input.style.height = `${clamped}px`;
  input.style.overflowY = input.scrollHeight > MAX_INPUT_HEIGHT ? 'auto' : 'hidden';
}
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(180deg, #f7f8fc 0%, #ffffff 100%);
  padding: 2rem 2.5rem 2rem 4.5rem;
}

.chat-window__topbar {
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
  border-bottom: 1px solid rgba(189, 201, 255, 0.6);
  padding: 0.5rem 0 0.45rem;
  margin-bottom: -1.3rem;
}

.chat-window__top-actions {
  display: flex;
  gap: 0.6rem;
  margin-top: -1.5rem;
}

.chat-window__top-button {
  border: 1px solid #dfe4ff;
  background: linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%);
  color: #1f2a56;
  border-radius: 18px;
  padding: 0.6rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease, box-shadow 0.2s ease, transform 0.1s ease;
  box-shadow: 0 12px 28px rgba(26, 40, 90, 0.12);
  font-size: 0.95rem;
}

.chat-window__top-button:hover {
  background: #f6f8ff;
  transform: translateY(-1px);
}

.chat-window__top-button--danger {
  background: linear-gradient(135deg, #ff8484, #ff4b4b);
  color: #fff;
  border: none;
}

.chat-window__top-button--danger:hover {
  background: linear-gradient(135deg, #ff6f6f, #ff3a3a);
}

.chat-window__top-flag {
  font-size: 1.05rem;
  line-height: 1;
  display: inline-flex;
}

.chat-window__domains {
  position: relative;
  display: inline-flex;
}

.chat-window__domains-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: none;
  background: rgba(218, 239, 255, 0.85);
  color: #1f8fe5;
  font-weight: 600;
  font-size: 0.95rem;
  border-radius: 18px;
  padding: 0.65rem 1.1rem;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.chat-window__domains-toggle:hover {
  background: rgba(193, 229, 255, 0.95);
  transform: translateY(-1px);
}

.chat-window__domains-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.chat-window__domains-caret {
  font-size: 0.85rem;
  color: #1f8fe5;
  transform: translateY(1px);
}

.chat-window__domains-badge {
  background: #1f8fe5;
  color: #fff;
  border-radius: 12px;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
}

.chat-window__domains-panel {
  position: absolute;
  left: 0;
  bottom: calc(100% + 0.65rem);
  width: 280px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 18px 40px rgba(26, 40, 90, 0.15);
  padding: 1rem 1.25rem 1.25rem;
  z-index: 10;
}

.chat-window__domains-panel--scrollable {
  --chat-window-domain-row-height: 2.55rem;
  --chat-window-domain-row-gap: 0.5rem;

  max-height: 600px;
  display: flex;
  flex-direction: column;
  overscroll-behavior: contain;
}

.chat-window__domains-panel--scrollable .chat-window__domains-grid {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  max-height: 300px;
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
  min-height: var(--chat-window-domain-row-height, auto);
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.chat-window__domains-option:hover {
  background-color: rgba(31, 143, 229, 0.08);
}

.chat-window__domains-option input {
  accent-color: #1f8fe5;
}

.chat-window__domains-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.chat-window__domains-apply {
  border: none;
  background: linear-gradient(135deg, #3cc3ff, #1f8fe5);
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

.chat-status-enter-active,
.chat-status-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.chat-status-enter-from,
.chat-status-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.chat-window__streaming {
  align-self: flex-start;
  display: flex;
  gap: 0.75rem;
  align-items: center;
  background: rgba(31, 143, 229, 0.12);
  color: #1f8fe5;
  font-weight: 600;
  padding: 0.65rem 1.1rem;
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(31, 143, 229, 0.12);
}

.chat-window__streaming--thinking {
  background: rgba(123, 91, 255, 0.12);
  color: #5a50b5;
  box-shadow: 0 12px 24px rgba(123, 91, 255, 0.15);
}

.chat-window__streaming-label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.chat-window__progress {
  flex: 0 0 160px;
  width: 160px;
  height: 6px;
  background: rgba(90, 80, 181, 0.14);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

.chat-window__progress-bar {
  position: absolute;
  inset: 0 auto 0 0;
  width: 0%;
  background: linear-gradient(90deg, #a68bff 0%, #5a50b5 100%);
  border-radius: inherit;
  transition: width 0.6s ease-out;
  box-shadow: 0 6px 12px rgba(90, 80, 181, 0.18);
}

.chat-window__streaming-label--pulse {
  animation: statusPulse 1.4s ease-in-out infinite;
}

.chat-window__streaming--stopped {
  background: rgba(91, 191, 123, 0.14);
  color: #2b9d63;
  box-shadow: 0 12px 24px rgba(43, 157, 99, 0.18);
}

.chat-window__streaming--paused {
  background: rgba(240, 168, 46, 0.14);
  color: #c2800a;
  box-shadow: 0 12px 24px rgba(240, 168, 46, 0.2);
}

.chat-window__stop {
  border: none;
  background: linear-gradient(135deg, #ff7b7b, #ff3c3c);
  color: #fff;
  font-weight: 700;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  box-shadow: 0 8px 18px rgba(255, 60, 60, 0.2);
}

.chat-window__stop:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(255, 60, 60, 0.3);
}

.chat-window__stop--restart {
  background: linear-gradient(135deg, #3cc3ff, #1f8fe5);
  box-shadow: 0 8px 18px rgba(31, 143, 229, 0.25);
}

@keyframes statusPulse {
  0% {
    opacity: 0.65;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-1px);
  }
  100% {
    opacity: 0.65;
    transform: translateY(0);
  }
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
  background: linear-gradient(135deg, #3cc3ff, #1f8fe5);
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

.chat-message__content :deep(a) {
  color: #1f8fe5;
  text-decoration: underline;
  word-break: break-all;
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
  line-height: 1.5;
  background: transparent;
  min-height: 44px;
  max-height: 240px;
  overflow-y: hidden;
}

.chat-window__composer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(189, 201, 255, 0.6);
  flex-wrap: wrap;
}

.chat-window__send {
  border: none;
  border-radius: 999px;
  padding: 0.6rem 1.6rem;
  font-weight: 600;
  background: linear-gradient(135deg, #3cc3ff, #1f8fe5);
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  margin-left: auto;
}

.chat-window__send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(31, 143, 229, 0.25);
}

.chat-window__send:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
