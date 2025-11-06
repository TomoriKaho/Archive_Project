import { defineStore } from 'pinia';
import {
  fetchDomains,
  createDomain,
  updateDomain,
  deleteDomain
} from '@/services/domains';
import { useUiStore } from './ui';

export const useDomainsStore = defineStore('domains', {
  state: () => ({
    items: [],
    isLoading: false
  }),
  actions: {
    async loadDomains() {
      this.isLoading = true;
      try {
        const { data } = await fetchDomains();
        this.items = data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to load domains.'
        });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async create(payload) {
      try {
        const body = {
          name: payload.name,
          description: payload.description || null
        };
        await createDomain(body);
        useUiStore().showToast({ type: 'success', message: 'Domain created.' });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to create domain.'
        });
        throw error;
      }
    },
    async update(domainId, payload) {
      try {
        const body = {
          name: payload.name,
          description: payload.description || null
        };
        await updateDomain(domainId, body);
        useUiStore().showToast({ type: 'success', message: 'Domain updated.' });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to update domain.'
        });
        throw error;
      }
    },
    async remove(domainId) {
      try {
        await deleteDomain(domainId);
        useUiStore().showToast({ type: 'success', message: 'Domain deleted.' });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to delete domain.'
        });
        throw error;
      }
    }
  }
});
