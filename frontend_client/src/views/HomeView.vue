<template>
  <div class="home-view">
    <header class="brand">
      <h1>Archive Client</h1>
      <p class="tagline">智能问答与知识库检索入口</p>
    </header>

    <SearchHero @submit="handleSearch" />

    <div class="actions">
      <router-link class="history-link" :to="{ name: 'chat' }">
        查看历史会话
      </router-link>
    </div>
  </div>
</template>

<script>
import SearchHero from '@/components/SearchHero.vue';

export default {
  name: 'HomeView',
  components: {
    SearchHero
  },
  methods: {
    handleSearch(query) {
      if (!query) {
        return;
      }
      this.$router.push({ name: 'chat', query: { q: query } });
    }
  }
};
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 2.5rem;
  min-height: 100vh;
  padding: 2rem 1.5rem 3rem;
  text-align: center;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.brand h1 {
  font-size: 3rem;
  margin: 0;
  color: #1f2937;
}

.tagline {
  margin: 0.75rem 0 0;
  font-size: 1.1rem;
  color: #4b5563;
}

.actions {
  display: flex;
  justify-content: center;
}

.history-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  background: white;
  color: #4c51bf;
  font-weight: 600;
  box-shadow: 0 10px 30px rgba(76, 81, 191, 0.15);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.history-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(76, 81, 191, 0.25);
}

@media (max-width: 600px) {
  .brand h1 {
    font-size: 2.25rem;
  }

  .tagline {
    font-size: 1rem;
  }
}
</style>
