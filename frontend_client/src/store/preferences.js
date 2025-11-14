import { defineStore } from 'pinia';

function normalizeLanguage(value) {
  return value === 'en' ? 'en' : 'zh';
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
    language: 'zh',
    preferredDomainIds: []
  }),
  actions: {
    setLanguage(value) {
      this.language = normalizeLanguage(value);
    },
    toggleLanguage() {
      this.setLanguage(this.language === 'zh' ? 'en' : 'zh');
    },
    setPreferredDomainIds(domainIds) {
      this.preferredDomainIds = normalizeDomainIds(domainIds);
    }
  }
});
