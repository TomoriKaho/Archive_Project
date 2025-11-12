import { defineStore } from 'pinia';
import {
  fetchDocuments,
  fetchDocument,
  fetchDocumentChunks,
  fetchDocumentContent,
  createTextDocument,
  uploadCsvDocument,
  updateDocument,
  deleteDocument,
  cancelDocumentIndexing
} from '@/services/documents';
import { i18n } from '@/i18n';
import { useUiStore } from './ui';

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    items: [],
    total: 0,
    pendingUploads: [],
    filters: {
      search: '',
      sort_by: 'created_at',
      order: 'desc',
      domain_id: null
    },
    isLoading: false,
    activeDocument: null,
    activeChunks: [],
    activeContent: null,
    isLoadingContent: false
  }),
  getters: {
    displayItems(state) {
      return [...state.pendingUploads, ...state.items];
    },
    totalWithPending(state) {
      return state.total + state.pendingUploads.length;
    }
  },
  actions: {
    async loadDocuments(params = {}) {
      this.isLoading = true;
      try {
        const sortBy = params.sort_by ?? this.filters.sort_by;
        const order = params.order ?? this.filters.order;
        const domainId =
          params.domain_id !== undefined
            ? params.domain_id
            : this.filters.domain_id;
        const searchTerm =
          params.search !== undefined ? params.search : this.filters.search;
        const query = {
          sort_by: sortBy,
          order,
          limit: params.limit ?? 20,
          offset: params.offset ?? 0
        };
        if (domainId) {
          query.domain_id = domainId;
        }
        if (searchTerm) {
          query.search = searchTerm;
        }
        this.filters.sort_by = sortBy;
        this.filters.order = order;
        this.filters.domain_id = domainId ?? null;
        this.filters.search = searchTerm ?? '';
        const { data } = await fetchDocuments(query);
        const items = data.items || data;
        this.items = items;
        this.total = data.total || items.length;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.loadError')
        });
        throw error;
      } finally {
        this.isLoading = false;
      }
    },
    setSearch(search) {
      this.filters.search = search ?? '';
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
      this.activeDocument = null;
      this.activeChunks = [];
      this.activeContent = null;
      try {
        const { data } = await fetchDocument(documentUuid);
        this.activeDocument = data;
        try {
          const { data: chunkData } = await fetchDocumentChunks(documentUuid);
          this.activeChunks = chunkData ?? [];
        } catch (chunkError) {
          console.error('Failed to load document chunks', chunkError);
          this.activeChunks = [];
          useUiStore().showToast({
            type: 'warning',
            message: i18n.global.t('documents.toast.chunksError')
          });
        }
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.fetchError')
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
          message: i18n.global.t('documents.toast.createSuccess')
        });
        await this.loadDocuments();
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.createError')
        });
        throw error;
      }
    },
    addPendingUpload({ domainId, title }) {
      const tempId = `pending-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 8)}`;
      const placeholder = {
        id: tempId,
        tempId,
        uuid: null,
        title,
        domain_id: domainId,
        created_at: new Date().toISOString(),
        updated_at: null,
        isUploading: true,
        vector_index_status: 'pending',
        vector_indexed_chunks: 0,
        vector_total_chunks: 0,
        vector_index_error: null
      };
      this.pendingUploads = [placeholder, ...this.pendingUploads];
      return placeholder;
    },
    removePendingUpload(tempId) {
      this.pendingUploads = this.pendingUploads.filter(
        (item) => item.tempId !== tempId
      );
    },
    async waitForUploadCompletion({ tempId, domainId, title, attempt = 0 }) {
      const pendingItem = this.pendingUploads.find((item) => item.tempId === tempId);
      if (!pendingItem) {
        return;
      }

      const MAX_ATTEMPTS = 24;
      const POLL_INTERVAL = 5000;

      try {
        const { data } = await fetchDocuments({
          domain_id: domainId,
          search: title,
          sort_by: 'created_at',
          order: 'desc',
          limit: 10
        });
        const items = data.items || data;
        const match = items.find((item) => item.title === title);
        if (match) {
          this.removePendingUpload(tempId);
          useUiStore().showToast({
            type: 'success',
            message: i18n.global.t('documents.toast.uploadSuccess', { title })
          });
          await this.loadDocuments();
          return;
        }
      } catch (pollError) {
        console.error('Failed to poll document status', pollError);
      }

      if (attempt + 1 >= MAX_ATTEMPTS) {
        this.removePendingUpload(tempId);
        useUiStore().showToast({
          type: 'warning',
          message: i18n.global.t('documents.toast.uploadUnknown')
        });
        await this.loadDocuments();
        return;
      }

      setTimeout(() => {
        this.waitForUploadCompletion({
          tempId,
          domainId,
          title,
          attempt: attempt + 1
        });
      }, POLL_INTERVAL);
    },
    async uploadCsv({ domainId, title, file }) {
      const pendingUpload = this.addPendingUpload({ domainId, title });
      try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('mode', 'csv');
        formData.append('file', file);
        await uploadCsvDocument(domainId, formData);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.uploadSuccess', { title })
        });
        this.removePendingUpload(pendingUpload.tempId);
        await this.loadDocuments();
      } catch (error) {
        const isTimeout = error?.code === 'ECONNABORTED';
        const isNetworkIssue =
          !error?.response &&
          (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error');

        if (isTimeout || isNetworkIssue) {
          useUiStore().showToast({
            type: 'info',
            message: i18n.global.t('documents.toast.uploadInProgress')
          });
          this.waitForUploadCompletion({
            tempId: pendingUpload.tempId,
            domainId,
            title
          });
          return;
        }
        this.removePendingUpload(pendingUpload.tempId);
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.uploadError')
        });
        throw error;
      }
    },
    async loadDocumentContent(documentUuid, params = {}) {
      this.isLoadingContent = true;
      try {
        const { data } = await fetchDocumentContent(documentUuid, params);
        this.activeContent = data;
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.contentError')
        });
        throw error;
      } finally {
        this.isLoadingContent = false;
      }
    },
    resetActiveContent() {
      this.activeContent = null;
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
          message: i18n.global.t('documents.toast.updateSuccess')
        });
        await this.loadDocuments();
        return data;
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.updateError')
        });
        throw error;
      }
    },
    async removeDocument({ documentId, domainId }) {
      try {
        await deleteDocument(domainId, documentId);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.deleteSuccess')
        });
        await this.loadDocuments();
      } catch (error) {
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.deleteError')
        });
        throw error;
      }
    },
    async cancelIndexing({ documentId, domainId }) {
      const target = this.items.find((item) => item.id === documentId);
      if (target) {
        target._isCancelling = true;
      }
      try {
        const { data } = await cancelDocumentIndexing(domainId, documentId);
        if (target) {
          Object.assign(target, data, { _isCancelling: false });
        } else {
          await this.loadDocuments();
        }
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.cancelSuccess')
        });
        return data;
      } catch (error) {
        if (target) {
          target._isCancelling = false;
        }
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.cancelError')
        });
        throw error;
      }
    }
  }
});
