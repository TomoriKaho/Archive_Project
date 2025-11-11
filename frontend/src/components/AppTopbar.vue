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
    <div class="topbar__actions">
      <button class="topbar__locale" type="button" @click="toggleLocale">
        {{ locale.value === 'zh' ? t('app.switchToEnglish') : t('app.switchToChinese') }}
      </button>
      <div class="topbar__user" v-if="user">
        <div class="topbar__profile">
        <div class="topbar__avatar">{{ initials }}</div>
        <div>
          <div class="topbar__name">{{ displayName }}</div>
          <div class="topbar__role">
            {{ user.is_admin ? t('roles.admin') : t('roles.member') }}
          </div>
        </div>
      </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';

import { useAuthStore } from '@/store/auth';
import { useI18nStore } from '@/store/i18n';

const props = defineProps({
  title: {
    type: String,
    default: 'Archive AI'
  }
});

const authStore = useAuthStore();
const i18nStore = useI18nStore();
const { locale } = storeToRefs(i18nStore);
const { t } = useI18n();

const user = computed(() => authStore.user);

const displayName = computed(() => user.value?.full_name || user.value?.email);

const initials = computed(() => {
  const source = displayName.value || '';
  if (!source) return 'AA';
  return source
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
});

function toggleLocale() {
  i18nStore.toggleLocale();
}
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
.topbar__actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar__user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar__locale {
  background: #f3f4f6;
  border: none;
  padding: 10px 16px;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.topbar__locale:hover {
  background: #e5e7eb;
}
