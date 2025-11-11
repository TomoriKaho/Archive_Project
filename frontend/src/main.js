import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import router from './router';
import { useAuthStore } from './store/auth';
import { i18n } from './i18n';
import { useI18nStore } from './store/i18n';
import './assets/styles/main.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(i18n);

const i18nStore = useI18nStore();
const authStore = useAuthStore();
// Ensure locale watcher runs on initialization
i18nStore.setLocale(i18n.global.locale.value);
authStore.initialize();

app.use(router);

app.mount('#app');
