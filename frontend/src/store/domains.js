import { defineStore } from 'pinia';
import {
  fetchDomains,
  createDomain,
  updateDomain,
  deleteDomain
} from '@/services/domains';
import { i18n } from '@/i18n';
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
          message: i18n.global.t('domains.toast.loadError')
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
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.createSuccess')
        });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('domains.toast.createError')
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
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.updateSuccess')
        });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('domains.toast.updateError')
        });
        throw error;
      }
    },
    async remove(domainId) {
      try {
        await deleteDomain(domainId);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.deleteSuccess')
        });
        await this.loadDomains();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('domains.toast.deleteError')
        });
        throw error;
      }
    }
  }
});
