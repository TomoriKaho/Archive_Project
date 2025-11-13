<template>
  <nav class="conversation-list" aria-label="历史会话列表">
    <button
      v-for="conversation in conversations"
      :key="conversation.id"
      class="conversation-item"
      :class="{ active: conversation.id === activeId }"
      type="button"
      @click="$emit('select', conversation.id)"
    >
      <h3>{{ conversation.title }}</h3>
      <p v-if="conversation.updatedAt" class="timestamp">
        {{ conversation.updatedAt }}
      </p>
    </button>
    <p v-if="!conversations.length" class="empty-state">暂无历史会话</p>
  </nav>
</template>

<script>
export default {
  name: 'ConversationList',
  props: {
    conversations: {
      type: Array,
      default: () => []
    },
    activeId: {
      type: String,
      default: null
    }
  }
};
</script>

<style scoped>
.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.conversation-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  background: rgba(15, 23, 42, 0.35);
  border: none;
  border-radius: 1rem;
  padding: 0.9rem 1rem;
  color: inherit;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.conversation-item:hover {
  background: rgba(15, 23, 42, 0.5);
  transform: translateY(-1px);
}

.conversation-item.active {
  background: rgba(96, 165, 250, 0.25);
}

h3 {
  margin: 0;
  font-size: 1rem;
}

.timestamp {
  margin: 0;
  font-size: 0.75rem;
  color: rgba(226, 232, 240, 0.8);
}

.empty-state {
  color: rgba(226, 232, 240, 0.7);
  text-align: center;
  margin: 2rem 0 0;
}
</style>
