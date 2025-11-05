import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import router from './router';
import { useAuthStore } from './store/auth';
import './assets/styles/main.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const authStore = useAuthStore();
authStore.initialize();

app.use(router);

app.mount('#app');
