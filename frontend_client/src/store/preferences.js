import { defineStore } from 'pinia';

const LANGUAGE_STORAGE_KEY = 'client-language';

function normalizeLanguage(value) {
  return value === 'en' ? 'en' : 'zh';
}

function readStoredLanguage() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return stored ? normalizeLanguage(stored) : null;
}

function persistLanguage(value) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY, normalizeLanguage(value));
}

function normalizeDomainIds(domainIds) {
  if (!Array.isArray(domainIds)) {
    return [];
  }
  return Array.from(
    new Set(
      domainIds
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value))
    )
  ).sort((a, b) => a - b);
}

export const usePreferencesStore = defineStore('client-preferences', {
  state: () => ({
    language: readStoredLanguage() || 'zh',
    preferredDomainIds: []
  }),
  actions: {
    setLanguage(value) {
      this.language = normalizeLanguage(value);
      persistLanguage(this.language);
    },
    toggleLanguage() {
      this.setLanguage(this.language === 'zh' ? 'en' : 'zh');
    },
    setPreferredDomainIds(domainIds) {
      this.preferredDomainIds = normalizeDomainIds(domainIds);
    }
  }
});
