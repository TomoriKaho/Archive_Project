import { defineStore } from 'pinia';
import {
  fetchDocuments,
  fetchDocument,
  fetchDocumentChunks,
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
      order: 'desc',
      domain_id: null
    },
    isLoading: false,
    activeDocument: null,
    activeChunks: []
  }),
  actions: {
    async loadDocuments(params = {}) {
      this.isLoading = true;
      try {
        const sortBy = params.sort_by || this.filters.sort_by;
        const order = params.order || this.filters.order;
        const domainId =
          params.domain_id !== undefined
            ? params.domain_id
            : this.filters.domain_id;
        const query = {
          sort_by: sortBy,
          order,
          limit: params.limit ?? 20,
          offset: params.offset ?? 0
        };
        if (domainId) {
          query.domain_id = domainId;
        }
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
      this.filters.order = sortDirection;
    },
    setDomainFilter(domainId) {
      this.filters.domain_id = domainId;
    },
    async loadDocument(documentUuid) {
      this.isLoading = true;
      try {
        this.activeDocument = null;
        this.activeChunks = [];
        const [documentResponse, chunksResponse] = await Promise.all([
          fetchDocument(documentUuid),
          fetchDocumentChunks(documentUuid)
        ]);
        this.activeDocument = documentResponse.data;
        this.activeChunks = chunksResponse.data ?? [];
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
        const { domainId, title, content } = payload;
        const body = {
          title,
          content
        };
        const { data } = await createTextDocument(domainId, body);
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
    async uploadCsv({ domainId, title, file }) {
      try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('mode', 'csv');
        formData.append('file', file);
        await uploadCsvDocument(domainId, formData);
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
    async saveDocument({ documentId, domainId, title, metadata }) {
      try {
        const body = { title };
        if (metadata !== undefined && metadata !== null) {
          body.doc_metadata = metadata;
        }
        const { data } = await updateDocument(domainId, documentId, body);
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
    async removeDocument({ documentId, domainId }) {
      try {
        await deleteDocument(domainId, documentId);
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
