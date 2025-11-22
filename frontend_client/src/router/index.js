import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/store/auth';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue')
  },
  {
    path: '/',
    name: 'landing',
    component: () => import('@/views/LandingView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chat/:conversationId?',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  try {
    await authStore.initialize();
  } catch (error) {
    console.error('Authentication initialization failed', error);
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({
      name: 'login',
      query: to.fullPath && to.fullPath !== '/login' ? { redirect: to.fullPath } : {}
    });
  }

  if (['login', 'register'].includes(to.name) && authStore.isAuthenticated) {
    return next({ name: 'landing' });
  }

  return next();
});

export default router;
