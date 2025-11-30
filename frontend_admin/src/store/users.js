import { defineStore } from 'pinia';
import { deleteUser, fetchUsers, updateUser } from '@/services/users';
import { i18n } from '@/i18n';
import { useUiStore } from './ui';

export const useUsersStore = defineStore('users', {
  state: () => ({
    items: [],
    total: 0,
    isLoading: false,
    filters: {
      sort_by: 'created_at',
      order: 'desc',
      limit: 20,
      offset: 0
    }
  }),
  actions: {
    async loadUsers(params = {}) {
      this.isLoading = true;
      try {
        const sortBy = params.sort_by || this.filters.sort_by;
        const order = params.order || this.filters.order;
        const limit = params.limit ?? this.filters.limit;
        const offset = params.offset ?? this.filters.offset;
        const query = {
          ...params,
          sort_by: sortBy,
          order,
          limit,
          offset
        };
        const { data } = await fetchUsers(query);
        this.items = data.items || data;
        this.total = data.total ?? data.items?.length ?? data.length ?? 0;
        this.filters.sort_by = sortBy;
        this.filters.order = order;
        this.filters.limit = data.limit ?? limit;
        this.filters.offset = data.offset ?? offset;
      } catch (error) {
        if (![401, 403, 419].includes(error?.response?.status)) {
          useUiStore().showToast({
            type: 'error',
            message: i18n.global.t('users.toast.loadError')
          });
          throw error;
        }
        // Authentication errors are handled by the auth store; avoid throwing to
        // prevent unhandled errors when the user is redirected to login.
      } finally {
        this.isLoading = false;
      }
    },
    setSorting({ sortBy, sortDirection }) {
      this.filters.sort_by = sortBy;
      this.filters.order = sortDirection;
    },
    async saveUser(userId, payload) {
      try {
        const body = {};
        if (Object.prototype.hasOwnProperty.call(payload, 'email')) {
          const email = payload.email?.trim();
          if (email) {
            body.email = email.toLowerCase();
          }
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'full_name')) {
          const name = payload.full_name ?? '';
          body.full_name = name.trim();
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'is_admin')) {
          body.is_admin = !!payload.is_admin;
        }
        if (Object.prototype.hasOwnProperty.call(payload, 'password')) {
          const password = payload.password?.trim();
          if (password) {
            body.password = password;
          }
        }
        await updateUser(userId, body);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('users.toast.updateSuccess')
        });
        await this.loadUsers({
          sort_by: this.filters.sort_by,
          order: this.filters.order,
          limit: this.filters.limit,
          offset: this.filters.offset
        });
        return true;
      } catch (error) {
        const message =
          error?.response?.data?.detail ||
          i18n.global.t('users.toast.updateError');
        useUiStore().showToast({
          type: 'error',
          message
        });
        return false;
      }
    },
    async removeUser(userId) {
      const previousItems = [...this.items];
      this.items = this.items.filter((item) => item.id !== userId);

      try {
        await deleteUser(userId);
      } catch (error) {
        if (error?.response?.status !== 404) {
          this.items = previousItems;
          useUiStore().showToast({
            type: 'error',
            message: i18n.global.t('users.toast.deleteError')
          });
          throw error;
        }
      }

      try {
        await this.loadUsers({
          sort_by: this.filters.sort_by,
          order: this.filters.order,
          limit: this.filters.limit,
          offset: this.filters.offset
        });
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('users.toast.deleteSuccess')
        });
      } catch (loadError) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('users.toast.deleteError')
        });
        throw loadError;
      }
    }
  }
});
