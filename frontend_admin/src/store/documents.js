import { defineStore } from 'pinia';
import {
  fetchDocuments,
  fetchDocument,
  fetchDocumentChunks,
  fetchDocumentContent,
  createTextDocument,
  uploadCsvDocument,
  uploadJsonDocument,
  updateDocument,
  deleteDocument,
  cancelDocumentIndexing,
  pauseDocumentIndexing,
  resumeDocumentIndexing
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
    activeChunkPage: {
      items: [],
      total: 0,
      limit: 0,
      offset: 0
    },
    activeContent: null,
    isLoadingContent: false,
    isLoadingChunks: false
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
      this.activeChunkPage = {
        items: [],
        total: 0,
        limit: 0,
        offset: 0
      };
      this.activeContent = null;
      this.isLoadingChunks = false;
      try {
        const { data } = await fetchDocument(documentUuid);
        this.activeDocument = data;
        this.activeChunkPage.total = data?.vector_total_chunks ?? 0;
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
    async loadDocumentChunks({ documentUuid, limit = 100, offset = 0 } = {}) {
      if (!documentUuid) {
        return;
      }
      this.isLoadingChunks = true;
      try {
        const params = {};
        if (limit !== undefined && limit !== null) {
          params.limit = limit;
        }
        if (offset) {
          params.offset = offset;
        }
        const { data } = await fetchDocumentChunks(documentUuid, params);
        if (!this.activeDocument || this.activeDocument.uuid !== documentUuid) {
          return;
        }
        const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
        const total =
          typeof data?.total === 'number'
            ? data.total
            : this.activeDocument?.vector_total_chunks ?? items.length;
        const limitValue = typeof data?.limit === 'number' ? data.limit : limit ?? items.length;
        const offsetValue = typeof data?.offset === 'number' ? data.offset : offset;
        this.activeChunkPage = {
          items,
          total,
          limit: limitValue,
          offset: offsetValue
        };
        return this.activeChunkPage;
      } catch (chunkError) {
        if (!this.activeDocument || this.activeDocument.uuid !== documentUuid) {
          return;
        }
        console.error('Failed to load document chunks', chunkError);
        this.activeChunkPage = {
          items: [],
          total: this.activeDocument?.vector_total_chunks ?? 0,
          limit,
          offset
        };
        useUiStore().showToast({
          type: 'warning',
          message: i18n.global.t('documents.toast.chunksError')
        });
        throw chunkError;
      } finally {
        this.isLoadingChunks = false;
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
        this.removePendingUpload(pendingUpload.tempId);
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.uploadError')
        });
        throw error;
      }
    },
    async uploadJson({ domainId, title, file }) {
      const pendingUpload = this.addPendingUpload({ domainId, title });
      try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('mode', 'json');
        formData.append('file', file);
        await uploadJsonDocument(domainId, formData);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.uploadSuccess', { title })
        });
        this.removePendingUpload(pendingUpload.tempId);
        await this.loadDocuments();
      } catch (error) {
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
    async pauseIndexing({ documentId, domainId }) {
      const target = this.items.find((item) => item.id === documentId);
      if (target) {
        target._isPausing = true;
      }
      try {
        const { data } = await pauseDocumentIndexing(domainId, documentId);
        if (target) {
          Object.assign(target, data, { _isPausing: false });
        } else {
          await this.loadDocuments();
        }
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.pauseSuccess')
        });
        return data;
      } catch (error) {
        if (target) {
          target._isPausing = false;
        }
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.pauseError')
        });
        throw error;
      }
    },
    async resumeIndexing({ documentId, domainId }) {
      const target = this.items.find((item) => item.id === documentId);
      if (target) {
        target._isResuming = true;
      }
      try {
        const { data } = await resumeDocumentIndexing(domainId, documentId);
        if (target) {
          Object.assign(target, data, { _isResuming: false });
        } else {
          await this.loadDocuments();
        }
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.resumeSuccess')
        });
        return data;
      } catch (error) {
        if (target) {
          target._isResuming = false;
        }
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.resumeError')
        });
        throw error;
      }
    },
    async cancelUpload({ documentId, domainId }) {
      const target = this.items.find((item) => item.id === documentId);
      if (target) {
        target._isCancelling = true;
      }
      try {
        await deleteDocument(domainId, documentId);
        useUiStore().showToast({
          type: 'success',
          message: i18n.global.t('documents.toast.cancelUploadSuccess')
        });
        await this.loadDocuments();
        if (target) {
          target._isCancelling = false;
        }
      } catch (error) {
        if (target) {
          target._isCancelling = false;
        }
        useUiStore().showToast({
          type: 'error',
          message: i18n.global.t('documents.toast.cancelUploadError')
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
