import { defineStore } from 'pinia';
import router from '@/router';
import { i18n } from '@/i18n';
import { configureApi, getStoredToken, persistToken } from '@/services/api';
import {
  loginRequest,
  registerRequest,
  fetchCurrentUser
} from '@/services/auth';
import { useUiStore } from './ui';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null,
    user: null,
    status: 'idle',
    initialized: false,
    initializationPromise: null
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    isAdmin: (state) => Boolean(state.user?.is_admin)
  },
  actions: {
    async initialize() {
      if (this.initialized) {
        return;
      }

      if (this.initializationPromise) {
        return this.initializationPromise;
      }

      this.initializationPromise = (async () => {
        const token = getStoredToken();
        this.token = token || null;
        configureApi(this);

        if (!token) {
          return;
        }

        try {
          await this.refreshUser();
        } catch (error) {
          // refreshUser will handle token errors and trigger logout when needed
          if (!this.isAuthenticated) {
            return;
          }
          throw error;
        }
      })()
        .catch((error) => {
          // Surface initialization issues to callers so navigation guards can react
          throw error;
        })
        .finally(() => {
          this.initialized = true;
          this.initializationPromise = null;
        });

      return this.initializationPromise;
    },
    async login(credentials) {
      this.status = 'loading';
      try {
        const { data } = await loginRequest(credentials);
        const token = data.access_token || data.token;

        if (!token) {
          throw new Error(i18n.global.t('auth.errors.missingToken'));
        }

        this.token = token;
        persistToken(token);
        configureApi(this);
        await this.refreshUser();
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('auth.toast.loginSuccess')
        });
        router.push({ name: 'dashboard' });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message:
            error.response?.data?.message ||
            i18n.global.t('auth.toast.loginError')
        });
        throw error;
      } finally {
        this.status = 'idle';
      }
    },
    async register(payload) {
      this.status = 'loading';
      try {
        await registerRequest(payload);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('auth.toast.registerSuccess')
        });
        router.push({ name: 'login' });
      } catch (error) {
        const uiStore = useUiStore();
        const status = error.response?.status;
        let message =
          error.response?.data?.message ||
          i18n.global.t('auth.toast.registerError');

        if (status === 409) {
          message =
            error.response?.data?.message ||
            i18n.global.t('auth.toast.registerEmailTaken');
        }

        uiStore.showToast({
          type: 'error',
          message
        });
        throw error;
      } finally {
        this.status = 'idle';
      }
    },
    async refreshUser() {
      if (!this.token) return;
      try {
        const { data } = await fetchCurrentUser();
        this.user = data;
      } catch (error) {
        if ([401, 403, 419].includes(error.response?.status)) {
          this.handleAuthError();
        }
        throw error;
      }
    },
    logout() {
      this.token = null;
      this.user = null;
      persistToken(null);
      useUiStore().showToast({
        type: 'info',
        message: i18n.global.t('auth.toast.logout')
      });
      router.push({ name: 'login' });
    },
    handleAuthError() {
      if (!this.token) return;
      this.logout();
    }
  }
});
