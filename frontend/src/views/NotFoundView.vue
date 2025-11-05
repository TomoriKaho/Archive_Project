<template>
  <section class="not-found">
    <h2>Page not found</h2>
    <p>The page you're looking for doesn't exist.</p>
    <RouterLink class="button button--primary" :to="{ name: 'dashboard' }">
      Go back to dashboard
    </RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router';
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 60vh;
  text-align: center;
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
</style>
