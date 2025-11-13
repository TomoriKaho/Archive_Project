<template>
  <section class="search-hero">
    <form class="search-form" @submit.prevent="onSubmit">
      <div class="input-wrapper">
        <input
          v-model="query"
          type="text"
          placeholder="请输入问题或关键词…"
          aria-label="搜索问题或关键词"
        />
        <button type="submit">开始对话</button>
      </div>
    </form>
    <p class="hint">支持自然语言提问，也可检索知识库中的文档。</p>
  </section>
</template>

<script>
export default {
  name: 'SearchHero',
  emits: ['submit'],
  data() {
    return {
      query: ''
    };
  },
  methods: {
    onSubmit() {
      this.$emit('submit', this.query.trim());
    }
  }
};
</script>

<style scoped>
.search-hero {
  width: min(720px, 100%);
}

.search-form {
  width: 100%;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: white;
  border-radius: 999px;
  padding: 0.75rem;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.15);
}

input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1.1rem;
  padding: 0 1rem;
  background: transparent;
}

button {
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.75rem;
  background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.3);
}

.hint {
  margin-top: 1rem;
  color: #6b7280;
  font-size: 0.95rem;
}

@media (max-width: 600px) {
  .input-wrapper {
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }

  input {
    width: 100%;
    padding: 0.75rem 1rem;
    background: #f9fafb;
    border-radius: 0.75rem;
  }

  button {
    width: 100%;
  }
}
</style>
