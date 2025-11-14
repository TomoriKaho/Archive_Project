import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

import router from '@/router';
import { i18n, setActiveLocale, updateDocumentTitle } from '@/i18n';

export const useI18nStore = defineStore('i18n', () => {
  const locale = ref(i18n.global.locale.value);

  watch(
    locale,
    (value) => {
      const normalized = setActiveLocale(value);
      if (normalized !== value) {
        locale.value = normalized;
        return;
      }
      updateDocumentTitle(router.currentRoute.value);
    },
    { immediate: true }
  );

  function setLocale(value) {
    locale.value = value === 'en' ? 'en' : 'zh';
  }

  function toggleLocale() {
    setLocale(locale.value === 'zh' ? 'en' : 'zh');
  }

  return {
    locale,
    setLocale,
    toggleLocale
  };
});
