<template>
  <section class="chat-messages" aria-live="polite">
    <article
      v-for="(message, index) in normalizedMessages"
      :key="index"
      class="message"
      :class="message.role"
    >
      <div class="avatar" :aria-label="message.role === 'user' ? '用户' : '助手'">
        {{ message.role === 'user' ? '我' : 'AI' }}
      </div>
      <div class="bubble">
        <p>{{ message.content }}</p>
      </div>
    </article>
    <p v-if="!normalizedMessages.length" class="empty">还没有消息，试着发送一个问题吧。</p>
  </section>
</template>

<script>
export default {
  name: 'ChatMessages',
  props: {
    messages: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    normalizedMessages() {
      return (this.messages || []).map(message => ({
        role: message.role === 'user' ? 'user' : 'assistant',
        content: message.content || ''
      }));
    }
  }
};
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2rem 1rem;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.message {
  display: flex;
  gap: 0.9rem;
  margin-bottom: 1.5rem;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #6366f1;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.message.user .avatar {
  background: #1d4ed8;
}

.bubble {
  max-width: 640px;
  padding: 1rem 1.25rem;
  border-radius: 1rem;
  background: white;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  color: #111827;
  line-height: 1.6;
}

.message.user .bubble {
  background: #3b82f6;
  color: white;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.25);
}

.empty {
  text-align: center;
  color: #94a3b8;
  margin-top: 4rem;
}
</style>
