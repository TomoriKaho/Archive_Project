import { defineStore } from 'pinia';
import { deleteUser, fetchUsers, updateUser } from '@/services/users';
import { useUiStore } from './ui';

export const useUsersStore = defineStore('users', {
  state: () => ({
    items: [],
    isLoading: false
  }),
  actions: {
    async loadUsers(params = {}) {
      this.isLoading = true;
      try {
        const { data } = await fetchUsers(params);
        this.items = data.items || data;
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
        await this.loadUsers();
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
        await this.loadUsers();
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
