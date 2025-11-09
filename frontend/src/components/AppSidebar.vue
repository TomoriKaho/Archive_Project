<template>
  <aside :class="['sidebar', { 'sidebar--collapsed': props.collapsed }]">
    <div class="sidebar__brand" :class="{ 'sidebar__brand--collapsed': props.collapsed }">
      <span class="sidebar__brand-text">Archive AI</span>
      <span class="sidebar__brand-indicator" aria-hidden="true"></span>
    </div>
    <ul v-if="!props.collapsed" class="sidebar__menu">
      <li
        v-for="item in navigation"
        :key="item.name"
        class="sidebar__menu-item"
      >
        <RouterLink
          :to="item.to"
          class="sidebar__menu-button"
          :class="{ 'sidebar__menu-button--active': item.isActive }"
        >
          <span>{{ item.label }}</span>
        </RouterLink>
      </li>
    </ul>
    <div v-if="!props.collapsed" class="sidebar__footer">
      <button class="sidebar__menu-button" type="button" @click="logout">
        Logout
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';

import { useAuthStore } from '@/store/auth';

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
});

const route = useRoute();
const authStore = useAuthStore();

const baseNavigation = [
  {
    name: 'dashboard',
    label: 'Dashboard',
    to: { name: 'dashboard' },
    path: '/dashboard'
  },
  {
    name: 'documents',
    label: 'Documents',
    to: { name: 'documents' },
    path: '/documents'
  },
  { name: 'chat', label: 'Chat', to: { name: 'chat' }, path: '/chat' }
];

const adminNavigation = [
  {
    name: 'domains',
    label: 'Domains',
    to: { name: 'domains' },
    path: '/domains'
  },
  { name: 'users', label: 'Users', to: { name: 'users' }, path: '/users' }
];

const navigation = computed(() => {
  const items = [...baseNavigation];
  if (authStore.isAdmin) {
    items.push(...adminNavigation);
  }
  return items.map((item) => ({
    ...item,
    isActive: route.name === item.name || route.path.startsWith(item.path)
  }));
});

function logout() {
  authStore.logout();
}
</script>

<style scoped>
.sidebar {
  transition: width 0.2s ease;
}

.sidebar--collapsed {
  width: 20px;
  overflow: hidden;
}

.sidebar__brand {
  position: relative;
  display: flex;
  align-items: center;
}

.sidebar__brand-text {
  white-space: nowrap;
}

.sidebar__brand--collapsed {
  justify-content: center;
  padding: 24px 0;
}

.sidebar--collapsed .sidebar__brand-text {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

.sidebar__brand-indicator {
  display: none;
}

.sidebar--collapsed .sidebar__brand-indicator {
  display: inline-flex;
  width: 6px;
  height: 24px;
  border-radius: 999px;
  background-color: currentColor;
}

.sidebar--collapsed .sidebar__menu-button {
  text-align: center;
}

.sidebar--collapsed .sidebar__menu-button span {
  display: none;
}

.sidebar__footer {
  padding: 16px 24px 24px;
}
</style>
