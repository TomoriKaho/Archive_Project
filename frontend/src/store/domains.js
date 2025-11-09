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
    isLoading: false,
    filters: {
      sort_by: 'name',
      order: 'asc'
    }
  }),
  actions: {
    async loadDomains(params = {}) {
      this.isLoading = true;
      try {
        const sortBy = params.sort_by || this.filters.sort_by;
        const order = params.order || this.filters.order;
        const query = {
          ...params,
          sort_by: sortBy,
          order
        };
        const { data } = await fetchDomains(query);
        this.items = data;
        this.filters.sort_by = sortBy;
        this.filters.order = order;
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
    setSorting({ sortBy, sortDirection }) {
      this.filters.sort_by = sortBy;
      this.filters.order = sortDirection;
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
