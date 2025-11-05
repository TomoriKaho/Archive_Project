import { defineStore } from 'pinia';
import { fetchUsers, updateUser, inviteUser } from '@/services/users';
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
        useUiStore().showToast({ type: 'error', message: 'Failed to load users.' });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async saveUser(userId, payload) {
      try {
        await updateUser(userId, payload);
        useUiStore().showToast({ type: 'success', message: 'User updated.' });
        await this.loadUsers();
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Unable to update user.' });
        throw error;
      }
    },
    async invite(payload) {
      try {
        await inviteUser(payload);
        useUiStore().showToast({ type: 'success', message: 'Invitation sent.' });
      } catch (error) {
        useUiStore().showToast({ type: 'error', message: 'Unable to send invitation.' });
        throw error;
      }
    }
  }
});
