<template>
  <aside class="chat-sidebar">
    <header class="chat-sidebar__header">
      <div>
        <h2 class="chat-sidebar__title">{{ texts.title }}</h2>
        <p class="chat-sidebar__subtitle">{{ texts.subtitle }}</p>
      </div>
      <div class="chat-sidebar__header-actions">
        <button class="chat-sidebar__create" type="button" @click="$emit('create')">
          <span class="chat-sidebar__create-icon" aria-hidden="true">+</span>
          <span class="chat-sidebar__create-label">{{ texts.create }}</span>
        </button>
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
            <span class="chat-sidebar__item-title">{{ formatTitle(conversation.title) }}</span>
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
      <p>{{ texts.empty }}</p>
    </section>
    <footer class="chat-sidebar__footer">
      <button class="chat-sidebar__home" type="button" @click="$emit('go-home')">{{ texts.goHome }}</button>
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
      create: '新建',
      rename: '重命名',
      delete: '删除',
      empty: '还没有会话，点击“新建”开始提问。',
      goHome: '返回主页'
    })
  }
});

const emit = defineEmits(['select', 'create', 'rename', 'delete', 'go-home']);

const DEFAULT_TITLE = '未命名会话';
const MAX_TITLE_LENGTH = 18;

function handleRename(conversation) {
  emit('rename', conversation);
}

function handleDelete(conversation) {
  emit('delete', conversation);
}

function formatTitle(rawTitle) {
  const normalized = (rawTitle || DEFAULT_TITLE).trim() || DEFAULT_TITLE;
  if (normalized.length <= MAX_TITLE_LENGTH) {
    return normalized;
  }
  return `${normalized.slice(0, MAX_TITLE_LENGTH)}...`;
}
</script>

<style scoped lang="scss">
.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 320px;
  min-width: 280px;
  max-width: 360px;
  background: linear-gradient(180deg, #ffffff 0%, #f6f7fb 100%);
  border-right: 1px solid #e1e8ff;
  height: 100vh;
  padding: 1.5rem 1.25rem 1.25rem;
}

.chat-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.chat-sidebar__header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  font-weight: 600;
  padding: 0.55rem 1.4rem;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
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
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.25);
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
  border-color: #7b5bff;
  box-shadow: 0 4px 12px rgba(123, 91, 255, 0.15);
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
  padding: 2rem 1rem;
  color: #6f7dae;
  font-size: 0.9rem;
  text-align: center;
}

.chat-sidebar__footer {
  margin-top: auto;
  padding-top: 1.5rem;
}

.chat-sidebar__home {
  width: 100%;
  border: none;
  background: rgba(74, 92, 200, 0.12);
  color: #4a5cc8;
  font-weight: 600;
  padding: 0.6rem 1rem;
  border-radius: 12px;
  cursor: pointer;
}

.chat-sidebar__home:hover {
  background: rgba(74, 92, 200, 0.2);
}
</style>
