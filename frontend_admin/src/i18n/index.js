import { createI18n } from 'vue-i18n';

import { messages } from './messages';

function resolveInitialLocale() {
  if (typeof window === 'undefined') {
    return 'zh';
  }

  const stored = window.localStorage.getItem('app-locale');
  if (stored === 'en' || stored === 'zh') {
    return stored;
  }

  return 'zh';
}

export const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: 'en',
  messages
});

export function setActiveLocale(locale) {
  const normalized = locale === 'en' ? 'en' : 'zh';
  i18n.global.locale.value = normalized;

  if (typeof window !== 'undefined') {
    window.localStorage.setItem('app-locale', normalized);
  }

  return normalized;
}

export function translateRouteTitle(route) {
  if (!route) return i18n.global.t('app.name');
  const titleKey = route.meta?.titleKey;
  if (!titleKey) {
    return i18n.global.t('app.name');
  }
  return i18n.global.t(titleKey);
}

export function updateDocumentTitle(route) {
  if (typeof document === 'undefined') {
    return;
  }

  const pageTitle = translateRouteTitle(route);
  document.title = `${pageTitle} · ${i18n.global.t('app.name')}`;
}
