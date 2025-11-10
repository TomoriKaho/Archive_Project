import { defineStore } from 'pinia';
import router from '@/router';
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
          throw new Error('No access token received from the server.');
        }

        this.token = token;
        persistToken(token);
        configureApi(this);
        await this.refreshUser();
        useUiStore().showToast({
          type: 'success',
          message: 'Logged in successfully.'
        });
        router.push({ name: 'dashboard' });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message:
            error.response?.data?.message ||
            'Unable to login. Check your credentials.'
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
          message: 'Account created. Please login.'
        });
        router.push({ name: 'login' });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message:
            error.response?.data?.message ||
            'Unable to register. Please try again.'
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
        message: 'You have been logged out.'
      });
      router.push({ name: 'login' });
    },
    handleAuthError() {
      if (!this.token) return;
      this.logout();
    }
  }
});
