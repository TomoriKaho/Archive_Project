<template>
  <form class="chat-composer" @submit.prevent="onSubmit">
    <textarea
      v-model="draft"
      :placeholder="placeholder"
      rows="1"
      @keydown.enter.exact.prevent="onSubmit"
    />
    <button type="submit">发送</button>
  </form>
</template>

<script>
export default {
  name: 'ChatComposer',
  props: {
    placeholder: {
      type: String,
      default: '请输入您的问题…'
    },
    initialQuery: {
      type: String,
      default: ''
    }
  },
  emits: ['send'],
  data() {
    return {
      draft: this.initialQuery
    };
  },
  watch: {
    initialQuery(newValue) {
      if (newValue && !this.draft) {
        this.draft = newValue;
      }
    }
  },
  methods: {
    onSubmit() {
      const content = this.draft.trim();
      if (!content) {
        return;
      }
      this.$emit('send', content);
      this.draft = '';
    }
  }
};
</script>

<style scoped>
.chat-composer {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  padding: 1.5rem 2rem 1.75rem;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

textarea {
  flex: 1;
  min-height: 60px;
  max-height: 160px;
  resize: vertical;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border: 1px solid #cbd5f5;
  font-size: 1rem;
  line-height: 1.6;
  font-family: inherit;
  background: #f8fafc;
}

textarea:focus {
  outline: 2px solid rgba(99, 102, 241, 0.4);
  border-color: #6366f1;
}

button {
  border: none;
  border-radius: 999px;
  padding: 0.8rem 1.8rem;
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(34, 211, 238, 0.35);
}

@media (max-width: 600px) {
  .chat-composer {
    flex-direction: column;
    align-items: stretch;
  }

  button {
    width: 100%;
  }
}
</style>
