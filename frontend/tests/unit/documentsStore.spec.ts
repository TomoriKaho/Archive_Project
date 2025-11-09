import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

const servicesMocks = vi.hoisted(() => ({
  fetchDocumentsMock: vi.fn(),
  fetchDocumentMock: vi.fn(),
  fetchDocumentChunksMock: vi.fn(),
  createTextDocumentMock: vi.fn(),
  uploadCsvDocumentMock: vi.fn(),
  updateDocumentMock: vi.fn(),
  deleteDocumentMock: vi.fn()
}));

const uiMocks = vi.hoisted(() => ({
  showToastMock: vi.fn()
}));

vi.mock('@/services/documents', () => ({
  fetchDocuments: servicesMocks.fetchDocumentsMock,
  fetchDocument: servicesMocks.fetchDocumentMock,
  fetchDocumentChunks: servicesMocks.fetchDocumentChunksMock,
  createTextDocument: servicesMocks.createTextDocumentMock,
  uploadCsvDocument: servicesMocks.uploadCsvDocumentMock,
  updateDocument: servicesMocks.updateDocumentMock,
  deleteDocument: servicesMocks.deleteDocumentMock
}));

vi.mock('@/store/ui', () => ({
  useUiStore: () => ({
    showToast: uiMocks.showToastMock
  })
}));

import { useDocumentsStore } from '@/store/documents';

describe('documents store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    servicesMocks.fetchDocumentsMock.mockReset();
    servicesMocks.fetchDocumentsMock.mockResolvedValue({ data: { items: [], total: 0 } });
    uiMocks.showToastMock.mockReset();
  });

  it('applies search filter when loading documents', async () => {
    const store = useDocumentsStore();

    await store.loadDocuments({ search: 'alpha' });

    expect(servicesMocks.fetchDocumentsMock).toHaveBeenCalledWith({
      sort_by: 'created_at',
      order: 'desc',
      limit: 20,
      offset: 0,
      search: 'alpha'
    });
    expect(store.filters.search).toBe('alpha');
  });

  it('clears search filter when not provided', async () => {
    const store = useDocumentsStore();

    await store.loadDocuments({ search: 'beta' });
    expect(store.filters.search).toBe('beta');

    store.setSearch('');
    await store.loadDocuments();

    expect(servicesMocks.fetchDocumentsMock).toHaveBeenLastCalledWith({
      sort_by: 'created_at',
      order: 'desc',
      limit: 20,
      offset: 0
    });
    expect(store.filters.search).toBe('');
  });
});
