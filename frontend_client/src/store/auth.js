import { defineStore } from 'pinia';
import router from '@/router';
import { configureApi, getStoredToken, persistToken } from '@/services/api';
import { loginRequest, registerRequest, fetchCurrentUser } from '@/services/auth';

export const useAuthStore = defineStore('client-auth', {
  state: () => ({
    token: null,
    user: null,
    status: 'idle',
    initialized: false,
    initializationPromise: null,
    error: null
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token)
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
        const storedToken = getStoredToken();
        this.token = storedToken || null;
        configureApi(this);

        if (!storedToken) {
          return;
        }

        try {
          await this.refreshUser();
        } catch (error) {
          if (!this.isAuthenticated) {
            return;
          }
          throw error;
        }
      })()
        .catch((error) => {
          console.error('Failed to initialize auth', error);
        })
        .finally(() => {
          this.initialized = true;
          this.initializationPromise = null;
        });

      return this.initializationPromise;
    },
    async login(credentials) {
      this.status = 'loading';
      this.error = null;
      try {
        const { data } = await loginRequest(credentials);
        const token = data?.access_token || data?.token;
        if (!token) {
          throw new Error('Missing access token');
        }
        this.token = token;
        persistToken(token);
        configureApi(this);
        await this.refreshUser();
        return true;
      } catch (error) {
        this.error = error;
        throw error;
      } finally {
        this.status = 'idle';
      }
    },
    async register(payload) {
      this.status = 'loading';
      this.error = null;
      try {
        await registerRequest(payload);
        return true;
      } catch (error) {
        this.error = error;
        throw error;
      } finally {
        this.status = 'idle';
      }
    },
    async refreshUser() {
      if (!this.token) {
        return;
      }
      try {
        const { data } = await fetchCurrentUser();
        this.user = data;
      } catch (error) {
        if ([401, 403, 419].includes(error.response?.status)) {
          this.handleAuthError();
          return;
        }
        throw error;
      }
    },
    logout() {
      this.token = null;
      this.user = null;
      persistToken(null);
      router.push({ name: 'login' }).catch(() => {});
    },
    handleAuthError() {
      if (!this.token) {
        return;
      }
      this.logout();
    }
  }
});
