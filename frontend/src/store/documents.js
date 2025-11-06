import { defineStore } from 'pinia';
import {
  fetchDocuments,
  fetchDocument,
  createTextDocument,
  uploadCsvDocument,
  updateDocument,
  deleteDocument
} from '@/services/documents';
import { useUiStore } from './ui';

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    items: [],
    total: 0,
    filters: {
      search: '',
      sort_by: 'created_at',
      sort_direction: 'desc'
    },
    isLoading: false,
    activeDocument: null
  }),
  actions: {
    async loadDocuments(params = {}) {
      this.isLoading = true;
      try {
        const query = { ...this.filters, ...params };
        const { data } = await fetchDocuments(query);
        this.items = data.items || data;
        this.total = data.total || data.length;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to load documents.'
        });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    setSearch(search) {
      this.filters.search = search;
    },
    setSorting({ sortBy, sortDirection }) {
      this.filters.sort_by = sortBy;
      this.filters.sort_direction = sortDirection;
    },
    async loadDocument(documentId) {
      this.isLoading = true;
      try {
        const { data } = await fetchDocument(documentId);
        this.activeDocument = data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Unable to fetch document.'
        });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    async createDocument(payload) {
      try {
        const { data } = await createTextDocument(payload);
        useUiStore().showToast({
          type: 'success',
          message: 'Document created successfully.'
        });
        await this.loadDocuments();
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to create document.'
        });
        throw error;
      }
    },
    async uploadCsv(formData) {
      try {
        await uploadCsvDocument(formData);
        useUiStore().showToast({
          type: 'success',
          message: 'CSV uploaded successfully.'
        });
        await this.loadDocuments();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to upload CSV.'
        });
        throw error;
      }
    },
    async saveDocument(documentId, payload) {
      try {
        const { data } = await updateDocument(documentId, payload);
        useUiStore().showToast({
          type: 'success',
          message: 'Document updated successfully.'
        });
        await this.loadDocuments();
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to update document.'
        });
        throw error;
      }
    },
    async removeDocument(documentId) {
      try {
        await deleteDocument(documentId);
        useUiStore().showToast({
          type: 'success',
          message: 'Document deleted.'
        });
        await this.loadDocuments();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: 'Failed to delete document.'
        });
        throw error;
      }
    }
  }
});
