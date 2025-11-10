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
    pendingUploads: [],
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
          message: 'Failed to load documents.'
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
        isUploading: true
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
            message: `${title} 文档上传成功。`
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
          message: '无法确认文档上传状态，请稍后刷新页面。'
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
          message: `${title} 文档上传成功。`
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
            message: '文档较大，正在后台继续处理。完成后将出现在文档列表中。'
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
