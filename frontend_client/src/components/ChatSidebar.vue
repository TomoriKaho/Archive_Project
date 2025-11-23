<template>
  <aside class="chat-sidebar">
    <header class="chat-sidebar__header">
      <div class="chat-sidebar__header-actions">
        <button class="chat-sidebar__home" type="button" @click="$emit('go-home')">{{ texts.goHome }}</button>
        <button class="chat-sidebar__collapse" type="button" @click="$emit('collapse')" :aria-label="texts.collapse">
          <svg class="chat-sidebar__collapse-icon" viewBox="0 0 32 32" role="presentation" aria-hidden="true">
            <line x1="21" y1="6" x2="21" y2="26" />
            <path d="M13 10.5 8 16l5 5.5" />
          </svg>
          <span class="chat-sidebar__collapse-tooltip" role="tooltip">{{ texts.collapse }}</span>
          <span class="chat-sidebar__sr-only">{{ texts.collapse }}</span>
        </button>
      </div>
      <hr class="chat-sidebar__divider" aria-hidden="true" />
      <div>
        <h2 class="chat-sidebar__title">{{ texts.title }}</h2>
        <p class="chat-sidebar__subtitle">{{ texts.subtitle }}</p>
      </div>
    </header>
    <section class="chat-sidebar__list" v-if="conversations.length">
      <ul>
        <li
          v-for="conversation in conversations"
          :key="conversation.id"
          :class="['chat-sidebar__item', { 'chat-sidebar__item--active': conversation.id === activeConversationId }]"
        >
          <button
            class="chat-sidebar__item-button"
            type="button"
            @click="$emit('select', conversation.id)"
          >
            <span class="chat-sidebar__item-title" :title="getFullTitle(conversation.title)">
              {{ formatTitle(conversation.title) }}
            </span>
          </button>
          <div class="chat-sidebar__item-actions">
            <button type="button" class="chat-sidebar__icon" @click="handleRename(conversation)">
              {{ texts.rename }}
            </button>
            <button type="button" class="chat-sidebar__icon chat-sidebar__icon--danger" @click="handleDelete(conversation)">
              {{ texts.delete }}
            </button>
          </div>
        </li>
      </ul>
    </section>
    <section v-else class="chat-sidebar__empty">
      <p class="chat-sidebar__empty-text">{{ texts.empty }}</p>
    </section>

    <footer class="chat-sidebar__footer">
      <button class="chat-sidebar__create" type="button" @click="$emit('create')">
        <span class="chat-sidebar__create-icon" aria-hidden="true">+</span>
        <span class="chat-sidebar__create-label">{{ texts.create }}</span>
      </button>
    </footer>
  </aside>
</template>

<script setup>
const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  activeConversationId: {
    type: Number,
    default: null
  },
  texts: {
    type: Object,
    default: () => ({
      title: '会话历史',
      subtitle: '管理你的提问与回答',
      create: '新建会话',
      rename: '重命名',
      delete: '删除',
      empty: '还没有会话，点击“新建会话”开始提问。',
      goHome: '返回主页',
      collapse: '收起边栏'
    })
  }
});

const emit = defineEmits(['select', 'create', 'rename', 'delete', 'go-home', 'collapse']);

const DEFAULT_TITLE = '未命名会话';
const MAX_TITLE_LENGTH = 18;

function handleRename(conversation) {
  emit('rename', conversation);
}

function handleDelete(conversation) {
  emit('delete', conversation);
}

function formatTitle(rawTitle) {
  const normalized = getFullTitle(rawTitle);
  if (normalized.length <= MAX_TITLE_LENGTH) {
    return normalized;
  }
  return `${normalized.slice(0, MAX_TITLE_LENGTH)}...`;
}

function getFullTitle(rawTitle) {
  return (rawTitle || DEFAULT_TITLE).trim() || DEFAULT_TITLE;
}
</script>

<style scoped lang="scss">
.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 280px;
  min-width: 240px;
  max-width: 320px;
  background: linear-gradient(180deg, #ffffff 0%, #f6f7fb 100%);
  border-right: 1px solid #e1e8ff;
  height: 100vh;
  padding: 1.5rem 1.25rem 1.25rem;
}

.chat-sidebar__header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.chat-sidebar__header-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.chat-sidebar__title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
  color: #1f2a56;
}

.chat-sidebar__subtitle {
  margin: 0.35rem 0 0;
  color: #5a6b97;
  font-size: 0.85rem;
}

.chat-sidebar__create {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: none;
  background: linear-gradient(135deg, #3cc3ff, #1f8fe5);
  color: #fff;
  font-weight: 600;
  padding: 0.85rem 1.4rem;
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
  width: 100%;
  justify-content: center;
}

.chat-sidebar__create-icon {
  display: inline-block;
  font-size: 1rem;
  line-height: 1;
}

.chat-sidebar__create-label {
  line-height: 1;
}

.chat-sidebar__create:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(31, 143, 229, 0.25);
}

.chat-sidebar__divider {
  border: none;
  border-top: 1px solid #d8e0ff;
  margin: 0;
}

.chat-sidebar__footer {
  margin-top: auto;
  padding-top: 1rem;
}

.chat-sidebar__list {
  flex: 1;
  overflow-y: auto;
}

.chat-sidebar__list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-sidebar__item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid transparent;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-sidebar__item--active {
  border-color: #1f8fe5;
  box-shadow: 0 4px 12px rgba(31, 143, 229, 0.18);
}

.chat-sidebar__item-button {
  flex: 1;
  display: flex;
  text-align: left;
  background: none;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2a56;
  cursor: pointer;
  min-width: 0;
}

.chat-sidebar__item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sidebar__item-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 0.5rem;
  flex-shrink: 0;
}

.chat-sidebar__icon {
  border: none;
  background: none;
  color: #5260a5;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.chat-sidebar__icon:hover {
  background-color: rgba(82, 96, 165, 0.15);
}

.chat-sidebar__icon--danger {
  color: #ff6b6b;
}

.chat-sidebar__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
}

.chat-sidebar__empty-text {
  margin: 0;
  color: #6f7dae;
  font-size: 0.9rem;
  white-space: pre-line;
}

.chat-sidebar__home {
  border: none;
  background: #bde5ff;
  color: #1f8fe5;
  font-weight: 600;
  padding: 0.65rem 1.25rem;
  border-radius: 12px;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(31, 143, 229, 0.18);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.chat-sidebar__home:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(31, 143, 229, 0.24);
}

.chat-sidebar__collapse {
  border: 1px solid #d8e0ff;
  background: #fff;
  color: #1f2a56;
  font-weight: 600;
  padding: 0.55rem;
  border-radius: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  position: relative;
  width: 44px;
  height: 44px;
}

.chat-sidebar__collapse:hover {
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.chat-sidebar__collapse-icon {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: #4a5cc8;
  stroke-width: 2.25px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chat-sidebar__collapse-tooltip {
  position: absolute;
  top: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%) translateY(-6px);
  background: #1f2a56;
  color: #fff;
  padding: 0.4rem 0.65rem;
  border-radius: 10px;
  font-size: 0.8rem;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease, transform 0.2s ease;
  box-shadow: 0 8px 20px rgba(31, 42, 86, 0.2);
  z-index: 120;
}

.chat-sidebar__collapse:hover .chat-sidebar__collapse-tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.chat-sidebar__sr-only {
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
</style>
