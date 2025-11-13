<template>
  <aside :class="['sidebar', { 'sidebar--collapsed': props.collapsed }]">
    <div class="sidebar__brand" :class="{ 'sidebar__brand--collapsed': props.collapsed }">
      <span class="sidebar__brand-text">{{ t('app.name') }}</span>
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
        {{ t('navigation.logout') }}
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useI18n } from 'vue-i18n';

import { useAuthStore } from '@/store/auth';

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
});

const route = useRoute();
const authStore = useAuthStore();
const { t } = useI18n();

const baseNavigation = [
  {
    name: 'dashboard',
    labelKey: 'navigation.dashboard',
    to: { name: 'dashboard' },
    path: '/dashboard'
  },
  {
    name: 'chat',
    labelKey: 'navigation.chat',
    to: { name: 'chat' },
    path: '/chat'
  },
  {
    name: 'domains',
    labelKey: 'navigation.domains',
    to: { name: 'domains' },
    path: '/domains'
  },
  {
    name: 'documents',
    labelKey: 'navigation.documents',
    to: { name: 'documents' },
    path: '/documents'
  }
];

const navigation = computed(() => {
  const items = [...baseNavigation];

  if (authStore.isAdmin) {
    items.push(
      {
        name: 'users',
        labelKey: 'navigation.users',
        to: { name: 'users' },
        path: '/users'
      },
      {
        name: 'profile',
        labelKey: 'navigation.profile',
        to: { name: 'profile' },
        path: '/profile'
      }
    );
  } else {
    items.push({
      name: 'profile',
      labelKey: 'navigation.profile',
      to: { name: 'profile' },
      path: '/profile'
    });
  }

  return items.map((item) => ({
    ...item,
    label: t(item.labelKey),
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
