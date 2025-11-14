import { defineStore } from 'pinia';
import { fetchDomains } from '@/services/domains';

export const useDomainsStore = defineStore('client-domains', {
  state: () => ({
    items: [],
    isLoading: false
  }),
  actions: {
    async loadDomains({ force = false } = {}) {
      if (this.items.length && !force) {
        return;
      }
      this.isLoading = true;
      try {
        const { data } = await fetchDomains();
        this.items = Array.isArray(data) ? data : [];
      } finally {
        this.isLoading = false;
      }
    }
  }
});
