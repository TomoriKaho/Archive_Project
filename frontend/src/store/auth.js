import { defineStore } from 'pinia';
import router from '@/router';
import { configureApi, getStoredToken, persistToken } from '@/services/api';
import { loginRequest, registerRequest, fetchCurrentUser } from '@/services/auth';
import { useUiStore } from './ui';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null,
    user: null,
    status: 'idle',
    initialized: false
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    isAdmin: (state) => state.user?.role === 'admin'
  },
  actions: {
    initialize() {
      if (this.initialized) return;
      const token = getStoredToken();
      if (token) {
        this.token = token;
        configureApi(this);
        this.refreshUser().catch(() => {
          this.logout();
        });
      } else {
        configureApi(this);
      }
      this.initialized = true;
    },
    async login(credentials) {
      this.status = 'loading';
      try {
        const { data } = await loginRequest(credentials);
        this.token = data.token;
        persistToken(data.token);
        configureApi(this);
        await this.refreshUser();
        useUiStore().showToast({ type: 'success', message: 'Logged in successfully.' });
        router.push({ name: 'dashboard' });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: error.response?.data?.message || 'Unable to login. Check your credentials.'
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
        useUiStore().showToast({ type: 'success', message: 'Account created. Please login.' });
        router.push({ name: 'login' });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: error.response?.data?.message || 'Unable to register. Please try again.'
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
        this.handleAuthError();
        throw error;
      }
    },
    logout() {
      this.token = null;
      this.user = null;
      persistToken(null);
      useUiStore().showToast({ type: 'info', message: 'You have been logged out.' });
      router.push({ name: 'login' });
    },
    handleAuthError() {
      if (!this.token) return;
      this.logout();
    }
  }
});
