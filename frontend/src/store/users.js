import { defineStore } from 'pinia';
import { deleteUser, fetchUsers, updateUser } from '@/services/users';
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
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to load users.'
        });
        throw error;
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
        useUiStore().showToast({ type: 'success', message: 'User updated.' });
        await this.loadUsers({
          sort_by: this.filters.sort_by,
          order: this.filters.order,
          limit: this.filters.limit,
          offset: this.filters.offset
        });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to update user.'
        });
        throw error;
      }
    },
    async removeUser(userId) {
      try {
        await deleteUser(userId);
        useUiStore().showToast({
          type: 'success',
          message: 'User deleted.'
        });
        await this.loadUsers({
          sort_by: this.filters.sort_by,
          order: this.filters.order,
          limit: this.filters.limit,
          offset: this.filters.offset
        });
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to delete user.'
        });
        throw error;
      }
    }
  }
});
