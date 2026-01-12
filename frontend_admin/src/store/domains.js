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
      const uiStore = useUiStore();
      try {
        const body = {
          name: payload.name,
          description: payload.description || null,
          language: payload.language || null
        };
        await createDomain(body);
        uiStore.showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.createSuccess')
        });
        await this.loadDomains();
        return true;
      } catch (error) {
        if (
          error?.response?.status === 400 &&
          error.response?.data?.detail === 'domain name already exists'
        ) {
          uiStore.showToast({
            type: 'warning',
            message: i18n.global.t('domains.toast.duplicateName')
          });
          return false;
        } else {
          uiStore.showToast({
            type: 'error',
            message: i18n.global.t('domains.toast.createError')
          });
        }
        throw error;
      }
    },
    async update(domainId, payload) {
      const uiStore = useUiStore();
      try {
        const body = {
          name: payload.name,
          description: payload.description || null,
          language: payload.language || null
        };
        await updateDomain(domainId, body);
        uiStore.showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.updateSuccess')
        });
        await this.loadDomains();
        return true;
      } catch (error) {
        if (
          error?.response?.status === 400 &&
          error.response?.data?.detail === 'domain name already exists'
        ) {
          uiStore.showToast({
            type: 'warning',
            message: i18n.global.t('domains.toast.duplicateName')
          });
          return false;
        } else {
          uiStore.showToast({
            type: 'error',
            message: i18n.global.t('domains.toast.updateError')
          });
        }
        throw error;
      }
    },
    async remove(domainId) {
      const previousItems = [...this.items];
      this.items = this.items.filter((item) => item.id !== domainId);

      try {
        await deleteDomain(domainId);
      } catch (error) {
        if (error?.response?.status !== 404) {
          this.items = previousItems;
          useUiStore().showToast({
            type: 'error',
            message: i18n.global.t('domains.toast.deleteError')
          });
          throw error;
        }
      }

      try {
        await this.loadDomains();
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('domains.toast.deleteSuccess')
        });
      } catch (loadError) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('domains.toast.deleteError')
        });
        throw loadError;
      }
    }
  }
});
