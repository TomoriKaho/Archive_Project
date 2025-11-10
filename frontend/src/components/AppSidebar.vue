<template>
  <aside :class="['sidebar', { 'sidebar--collapsed': props.collapsed }]">
    <div class="sidebar__brand" :class="{ 'sidebar__brand--collapsed': props.collapsed }">
      <span class="sidebar__brand-text">Archive AI</span>
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
  width: 160px;
  overflow: hidden;
}

.sidebar__brand {
  display: flex;
  align-items: center;
}

.sidebar__brand-text {
  white-space: nowrap;
}

.sidebar__brand--collapsed {
  justify-content: center;
  padding: 24px 16px;
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
