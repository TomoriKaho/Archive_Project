<template>
  <header class="topbar">
    <div class="topbar__left">
      <button
        class="topbar__toggle"
        type="button"
        @click="$emit('toggle-sidebar')"
      >
        ☰
      </button>
      <h1 class="topbar__title">{{ title }}</h1>
    </div>
    <div class="topbar__actions" v-if="user">
      <div class="topbar__profile">
        <div class="topbar__avatar">{{ initials }}</div>
        <div>
          <div class="topbar__name">{{ user.name }}</div>
          <div class="topbar__role">{{ user.role }}</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue';

import { useAuthStore } from '@/store/auth';

const props = defineProps({
  title: {
    type: String,
    default: 'Archive AI'
  }
});

const authStore = useAuthStore();

const user = computed(() => authStore.user);

const initials = computed(() => {
  if (!user.value?.name) return 'AA';
  return user.value.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
});
</script>

<style scoped>
.topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar__toggle {
  background: #1f2937;
  border: none;
  color: #ffffff;
  border-radius: 8px;
  width: 40px;
  height: 40px;
  font-size: 18px;
  cursor: pointer;
}

.topbar__profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar__avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #3b82f6;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.topbar__name {
  font-weight: 600;
}

.topbar__role {
  font-size: 12px;
  color: #6b7280;
}
</style>
