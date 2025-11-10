import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/store/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { layout: 'auth', public: true, title: 'Login' }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { layout: 'auth', public: true, title: 'Register' }
    },
    {
      path: '/',
      redirect: { name: 'dashboard' }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true, title: 'Dashboard' }
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('@/views/DocumentsView.vue'),
      meta: { requiresAuth: true, title: 'Documents' }
    },
    {
      path: '/documents/:id',
      name: 'document-detail',
      component: () => import('@/views/DocumentDetailView.vue'),
      meta: { requiresAuth: true, title: 'Document Detail' }
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true, title: 'Chat' }
    },
    {
      path: '/domains',
      name: 'domains',
      component: () => import('@/views/DomainsView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true, title: 'Domains' }
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true, title: 'Users' }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { requiresAuth: true, title: 'Not Found' }
    }
  ]
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  try {
    await authStore.initialize();
  } catch (error) {
    // Initialization failures will be surfaced through auth store toasts; continue navigation
  }

  if (!to.meta.public && !authStore.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } });
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'dashboard' });
  }

  return next();
});

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} · Archive AI`;
  }
});

export default router;
