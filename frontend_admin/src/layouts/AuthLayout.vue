<template>
  <div class="auth-shell">
    <div class="auth-panel">
      <button class="auth-panel__locale" type="button" @click="toggleLocale">
        {{ isChineseLocale
          ? t('app.switchToEnglish')
          : t('app.switchToChinese')
        }}
      </button>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';

import { useI18nStore } from '@/store/i18n';

const i18nStore = useI18nStore();
const { locale } = storeToRefs(i18nStore);
const { t } = useI18n();

const isChineseLocale = computed(() => locale.value?.startsWith('zh'));

function toggleLocale() {
  i18nStore.toggleLocale();
}
</script>

<style scoped>
.auth-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1f2937, #3b82f6);
  padding: 24px;
}

.auth-panel {
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.25);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
}

.auth-panel__locale {
  align-self: flex-end;
  margin-bottom: 24px;
  background: rgba(15, 23, 42, 0.08);
  border: none;
  border-radius: 999px;
  padding: 8px 16px;
  font-weight: 600;
  cursor: pointer;
}

.auth-panel__locale:hover {
  background: rgba(15, 23, 42, 0.12);
}
</style>
