<template>
  <section v-if="document" class="document-detail">
    <header class="document-detail__header">
      <div>
        <h2>{{ document.title }}</h2>
        <p>Domain: {{ domainName }}</p>
      </div>
      <div class="document-detail__actions">
        <button class="button" type="button" @click="openEdit">Edit</button>
        <button class="button button--danger" type="button" @click="openDelete">
          Delete
        </button>
      </div>
    </header>

    <div class="document-detail__meta">
      <div>
        <span class="label">Created</span>
        <span>{{ formatDate(document.created_at) }}</span>
      </div>
      <div>
        <span class="label">Updated</span>
        <span>{{ formatDate(document.updated_at) }}</span>
      </div>
      <div>
        <span class="label">UUID</span>
        <span class="mono">{{ document.uuid }}</span>
      </div>
      <div>
        <span class="label">Domain ID</span>
        <span>{{ document.domain_id }}</span>
      </div>
    </div>

    <article class="document-detail__content document-detail__source">
      <details @toggle="onContentToggle" :open="isContentExpanded">
        <summary class="document-content__summary">
          <span>Document content</span>
          <span v-if="contentRangeLabel" class="document-content__summary-range">
            {{ contentRangeLabel }}
          </span>
        </summary>
        <div class="document-detail__source-body">
          <p v-if="contentError" class="document-detail__error">{{ contentError }}</p>
          <p v-else-if="isContentLoading" class="document-detail__loading-text">
            Loading content…
          </p>
          <template v-else>
            <p
              v-if="contentPage && !contentItems.length"
              class="document-detail__empty"
            >
              No original content is available for this document.
            </p>
            <template v-else>
              <div
                v-if="contentPage && contentPageOptions.length"
                class="document-detail__pager"
              >
                <label class="document-detail__pager-label" for="content-page-select"
                  >Range</label
                >
                <select
                  id="content-page-select"
                  v-model.number="contentPageIndex"
                  class="document-detail__pager-select"
                  @change="changeContentPage"
                >
                  <option
                    v-for="option in contentPageOptions"
                    :key="option.index"
                    :value="option.index"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </div>
              <ol
                v-if="contentPage && contentPage.mode === 'text' && contentPage.lines.length"
                :start="contentListStart"
                class="document-content__text"
              >
                <li v-for="(line, index) in contentPage.lines" :key="index">
                  {{ line || '\u00A0' }}
                </li>
              </ol>
              <div
                v-else-if="contentPage && contentPage.mode === 'csv' && normalizedRows.length"
                class="document-content__table-wrapper"
              >
                <table class="document-content__table">
                  <thead>
                    <tr>
                      <th class="document-content__index-header"></th>
                      <th
                        v-for="(header, headerIndex) in contentHeaders"
                        :key="`header-${headerIndex}`"
                      >
                        {{ header }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(row, rowIndex) in normalizedRows"
                      :key="`row-${rowIndex}`"
                    >
                      <td class="document-content__index-cell">
                        {{ contentOffset + rowIndex + 1 }}
                      </td>
                      <td
                        v-for="(value, columnIndex) in row"
                        :key="`cell-${rowIndex}-${columnIndex}`"
                        class="document-content__cell"
                      >
                        <button
                          class="document-content__cell-button"
                          type="button"
                          @click="openCellPreview(columnIndex, value, contentOffset + rowIndex + 1)"
                        >
                          {{ formatCellPreview(value) }}
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </template>
          <div
            v-if="contentPage"
            class="document-detail__pager document-detail__pager--footer"
          >
            <span class="document-content__summary-helper">
              Total {{ contentPage.total }}
              {{ contentPage.mode === 'csv' ? 'rows' : 'lines' }}
            </span>
            <div
              v-if="contentPageOptions.length"
              class="document-detail__pager-actions"
            >
              <button
                class="document-detail__pager-button"
                type="button"
                :disabled="contentPageIndex === 0"
                @click="loadPreviousContentPage"
              >
                Previous
              </button>
              <button
                class="document-detail__pager-button"
                type="button"
                :disabled="contentPageIndex >= contentPageOptions.length - 1"
                @click="loadNextContentPage"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </details>
    </article>

    <article class="document-detail__content document-detail__chunks">
      <header class="document-detail__chunks-header">
        <div>
          <h3>Chunks</h3>
          <span class="document-detail__hint">
            {{ chunks.length }}
            {{ chunks.length === 1 ? 'chunk' : 'chunks' }}
            stored for this document.
            <template v-if="chunkRangeLabel">
              Currently viewing {{ chunkRangeLabel }}.
            </template>
          </span>
        </div>
        <div v-if="chunkPageOptions.length > 1" class="chunk-pagination">
          <label class="chunk-pagination__label" for="chunk-page-select">Range</label>
          <select
            id="chunk-page-select"
            v-model.number="chunkPageIndex"
            class="chunk-pagination__select"
          >
            <option
              v-for="option in chunkPageOptions"
              :key="option.index"
              :value="option.index"
            >
              {{ option.label }}
            </option>
          </select>
        </div>
      </header>
      <p v-if="!chunks.length" class="document-detail__empty">
        No chunks have been generated for this document yet.
      </p>
      <ul v-else class="chunk-list">
        <li v-for="chunk in visibleChunks" :key="chunk.id" class="chunk-list__item">
          <details>
            <summary>
              <span>Chunk {{ chunk.ordinal + 1 }}</span>
              <span class="chunk-list__meta">
                {{ formatChunkLength(chunk) }} characters
              </span>
            </summary>
            <pre>{{ chunk.content }}</pre>
          </details>
        </li>
      </ul>
    </article>
    <BaseModal v-model="isPreviewOpen" title="Cell content preview">
      <p class="document-content__preview-meta">
        Row {{ previewContent.rowNumber }} · {{ previewContent.header }}
      </p>
      <pre class="document-content__preview-value">{{ previewContent.value }}</pre>
      <template #footer>
        <button class="button" type="button" @click="closePreview">Close</button>
      </template>
    </BaseModal>

    <BaseModal v-model="isEditOpen" title="Edit Document">
      <div class="tab-pane">
        <div
          class="form-field"
          :class="{ 'form-field--error': editErrors.title }"
        >
          <label for="edit-title">Title</label>
          <input id="edit-title" v-model.trim="editForm.title" type="text" />
          <p v-if="editErrors.title" class="form-field__error">
            {{ editErrors.title }}
          </p>
        </div>
      </div>
      <template #footer>
        <button class="button" type="button" @click="closeEdit">Cancel</button>
        <button class="button button--primary" type="button" @click="save">
          {{ isSaving ? 'Saving…' : 'Save changes' }}
        </button>
      </template>
    </BaseModal>
    <BaseModal v-model="isDeleteOpen" title="Delete Document">
      <p>
        Deleting this document will remove it and all of its chunks permanently.
        This action cannot be undone. Are you sure you want to continue?
      </p>
      <template #footer>
        <button class="button" type="button" @click="closeDelete">
          Cancel
        </button>
        <button
          class="button button--danger"
          type="button"
          :disabled="isDeleting"
          @click="remove"
        >
          {{ isDeleting ? 'Deleting…' : 'Delete document' }}
        </button>
      </template>
    </BaseModal>
  </section>
  <section v-else class="document-detail__loading">Loading document…</section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import BaseModal from '@/components/BaseModal.vue';
import { useDocumentsStore } from '@/store/documents';
import { useDomainsStore } from '@/store/domains';

const route = useRoute();
const router = useRouter();
const documentsStore = useDocumentsStore();
const domainsStore = useDomainsStore();

const isEditOpen = ref(false);
const isDeleteOpen = ref(false);
const isDeleting = ref(false);
const isSaving = ref(false);

const chunkPageSize = 100;
const CELL_PREVIEW_LENGTH = 60;
const chunkPageIndex = ref(0);
const contentPageIndex = ref(0);
const isContentExpanded = ref(false);
const contentError = ref('');
const isPreviewOpen = ref(false);
const previewContent = reactive({
  header: '',
  value: '',
  rowNumber: 0
});

const editForm = reactive({
  title: ''
});

const editErrors = reactive({
  title: ''
});

const document = computed(() => documentsStore.activeDocument);
const chunks = computed(() => documentsStore.activeChunks || []);
const contentPage = computed(() => documentsStore.activeContent);
const isContentLoading = computed(() => documentsStore.isLoadingContent);
const domainName = computed(() => {
  const domain = domainsStore.items.find(
    (item) => item.id === document.value?.domain_id
  );
  if (!document.value) return '—';
  return domain?.name || `Domain #${document.value.domain_id}`;
});

const totalChunkPages = computed(() => {
  if (!chunks.value.length) return 0;
  return Math.ceil(chunks.value.length / chunkPageSize);
});

const chunkPageOptions = computed(() => {
  if (!chunks.value.length) return [];
  const totalPages = Math.ceil(chunks.value.length / chunkPageSize);
  return Array.from({ length: totalPages }, (_, index) => {
    const start = index * chunkPageSize + 1;
    const end = Math.min((index + 1) * chunkPageSize, chunks.value.length);
    return { index, label: `${start}-${end}` };
  });
});

const visibleChunks = computed(() => {
  if (!chunks.value.length) return [];
  const start = chunkPageIndex.value * chunkPageSize;
  return chunks.value.slice(start, start + chunkPageSize);
});

const chunkRangeLabel = computed(() => {
  if (!chunks.value.length) return '';
  const start = chunkPageIndex.value * chunkPageSize;
  const end = Math.min(start + chunkPageSize, chunks.value.length);
  return `${start + 1}-${end}`;
});

const contentHeaders = computed(() => {
  const page = contentPage.value;
  if (!page) return [];
  const headers = Array.isArray(page.headers) ? page.headers : [];
  if (headers.length) {
    return headers;
  }
  const rows = Array.isArray(page.rows) ? page.rows : [];
  const maxColumns = rows.reduce((max, row) => Math.max(max, row.length), 0);
  if (!maxColumns) return [];
  return Array.from({ length: maxColumns }, (_, index) => `Column ${index + 1}`);
});

const normalizedRows = computed(() => {
  const page = contentPage.value;
  if (!page || page.mode !== 'csv') return [];
  const headers = contentHeaders.value;
  const targetLength = headers.length || 0;
  if (!targetLength) {
    return Array.isArray(page.rows) ? page.rows : [];
  }
  return (Array.isArray(page.rows) ? page.rows : []).map((row) => {
    const cells = Array.isArray(row) ? [...row] : [String(row ?? '')];
    if (cells.length < targetLength) {
      return [...cells, ...Array(targetLength - cells.length).fill('')];
    }
    if (cells.length > targetLength) {
      return cells.slice(0, targetLength);
    }
    return cells;
  });
});

const contentItems = computed(() => {
  const page = contentPage.value;
  if (!page) return [];
  if (page.mode === 'csv') {
    return normalizedRows.value;
  }
  return Array.isArray(page.lines) ? page.lines : [];
});

const contentListStart = computed(() => {
  const page = contentPage.value;
  if (!page || !page.total) return 1;
  return Math.min(page.offset + 1, page.total);
});

const contentOffset = computed(() => contentPage.value?.offset ?? 0);

const contentRangeLabel = computed(() => {
  const page = contentPage.value;
  if (!page || !page.total) return '';
  const count = page.mode === 'csv'
    ? normalizedRows.value.length
    : (Array.isArray(page.lines) ? page.lines.length : 0);
  const start = Math.min(page.offset + 1, page.total);
  const end = Math.min(page.offset + count, page.total);
  return `${start}-${end} / ${page.total}`;
});

const contentPageOptions = computed(() => {
  const page = contentPage.value;
  if (!page || !page.total) return [];
  const limit = page.limit || (page.mode === 'csv' ? 20 : 100);
  if (!limit || page.total <= limit) return [];
  const totalPages = Math.ceil(page.total / limit);
  return Array.from({ length: totalPages }, (_, index) => {
    const start = index * limit + 1;
    const end = Math.min((index + 1) * limit, page.total);
    return { index, label: `${start}-${end}` };
  });
});

watch(chunks, () => {
  chunkPageIndex.value = 0;
});

watch(totalChunkPages, (total) => {
  if (!total) {
    chunkPageIndex.value = 0;
    return;
  }
  if (chunkPageIndex.value > total - 1) {
    chunkPageIndex.value = total - 1;
  }
});

watch(contentPage, (page) => {
  if (!page) {
    contentPageIndex.value = 0;
    return;
  }
  const limit = page.limit || (page.mode === 'csv' ? 20 : 100);
  const derived = limit ? Math.floor((page.offset ?? 0) / limit) : 0;
  contentPageIndex.value = derived;
  contentError.value = '';
});

watch(
  document,
  (value, oldValue) => {
    if (!value) {
      documentsStore.resetActiveContent();
      contentPageIndex.value = 0;
      contentError.value = '';
      isContentExpanded.value = false;
      isPreviewOpen.value = false;
      previewContent.header = '';
      previewContent.value = '';
      previewContent.rowNumber = 0;
      return;
    }
    if (!oldValue || value.uuid !== oldValue.uuid) {
      documentsStore.resetActiveContent();
      contentPageIndex.value = 0;
      contentError.value = '';
      isContentExpanded.value = false;
      isPreviewOpen.value = false;
      previewContent.header = '';
      previewContent.value = '';
      previewContent.rowNumber = 0;
    }
  },
  { immediate: false }
);

onMounted(async () => {
  if (!domainsStore.items.length) {
    await domainsStore.loadDomains();
  }
  await documentsStore.loadDocument(route.params.id);
});

watch(
  document,
  (value) => {
    if (!value) return;
    editForm.title = value.title;
  },
  { immediate: true }
);

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function openEdit() {
  isEditOpen.value = true;
}

function closeEdit() {
  isEditOpen.value = false;
}

function openDelete() {
  isDeleteOpen.value = true;
}

function closeDelete() {
  isDeleteOpen.value = false;
}

function formatChunkLength(chunk) {
  if (!chunk || typeof chunk.content !== 'string') return 0;
  return chunk.content.length;
}

async function loadContentPage(index) {
  if (!document.value) return;
  const current = contentPage.value;
  const baseLimit = current?.limit && current.limit > 0
    ? current.limit
    : current?.mode === 'csv'
      ? 20
      : 100;
  const params = {};
  const limitForOffset = current?.limit && current.limit > 0 ? current.limit : baseLimit;
  if (index > 0) {
    params.offset = index * limitForOffset;
  }
  if (current?.limit && current.limit > 0) {
    params.limit = current.limit;
  } else if (current && !current.limit && baseLimit) {
    params.limit = baseLimit;
  } else if (!current && index > 0) {
    params.limit = baseLimit;
  }
  contentError.value = '';
  try {
    const data = await documentsStore.loadDocumentContent(document.value.uuid, params);
    const effectiveLimit = data?.limit && data.limit > 0
      ? data.limit
      : limitForOffset || (data?.mode === 'csv' ? 20 : 100);
    const derivedIndex = effectiveLimit > 0
      ? Math.floor((data?.offset ?? 0) / effectiveLimit)
      : 0;
    contentPageIndex.value = derivedIndex;
  } catch (error) {
    contentError.value = 'Failed to load document content.';
  }
}

function onContentToggle(event) {
  const opened = Boolean(event?.target?.open);
  isContentExpanded.value = opened;
  if (opened && !contentPage.value && !isContentLoading.value) {
    loadContentPage(0);
  }
}

function changeContentPage() {
  loadContentPage(contentPageIndex.value);
}

function loadPreviousContentPage() {
  if (contentPageIndex.value <= 0) return;
  loadContentPage(contentPageIndex.value - 1);
}

function loadNextContentPage() {
  if (!contentPageOptions.value.length) return;
  const lastIndex = contentPageOptions.value.length - 1;
  if (contentPageIndex.value >= lastIndex) return;
  loadContentPage(contentPageIndex.value + 1);
}

function formatCellPreview(value) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const text = String(value);
  if (text.length > CELL_PREVIEW_LENGTH) {
    return `${text.slice(0, CELL_PREVIEW_LENGTH)}…`;
  }
  return text;
}

function openCellPreview(columnIndex, value, rowNumber) {
  const headers = contentHeaders.value;
  previewContent.header = headers[columnIndex] || `Column ${columnIndex + 1}`;
  previewContent.value = value === null || value === undefined ? '' : String(value);
  previewContent.rowNumber = rowNumber;
  isPreviewOpen.value = true;
}

function closePreview() {
  isPreviewOpen.value = false;
}

function validate() {
  editErrors.title = editForm.title ? '' : 'Title is required.';
  return !editErrors.title;
}

async function save() {
  if (!validate() || !document.value) return;
  isSaving.value = true;
  try {
    await documentsStore.saveDocument({
      documentId: document.value.id,
      domainId: document.value.domain_id,
      title: editForm.title,
      metadata: document.value.doc_metadata
    });
    await documentsStore.loadDocument(route.params.id);
    closeEdit();
  } finally {
    isSaving.value = false;
  }
}

async function remove() {
  if (!document.value) return;
  if (isDeleting.value) return;
  isDeleting.value = true;
  try {
    await documentsStore.removeDocument({
      documentId: document.value.id,
      domainId: document.value.domain_id
    });
    closeDelete();
    router.push({ name: 'documents' });
  } finally {
    isDeleting.value = false;
  }
}
</script>

<style scoped>
.document-detail {
  overflow-x: hidden;
}

.document-detail__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.document-detail__actions {
  display: flex;
  gap: 12px;
}

.document-detail__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.label {
  display: block;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
}

.mono {
  font-family: 'Fira Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 13px;
}

.document-detail__empty {
  color: #6b7280;
  margin-bottom: 16px;
}

.document-detail__content {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.document-detail__source {
  overflow: hidden;
  max-width: 100%;
}

.document-detail__content pre {
  background: #f3f4f6;
  padding: 16px;
  border-radius: 12px;
  overflow: auto;
}

.document-detail__hint {
  color: #6b7280;
  margin: 0 0 12px;
}

.document-detail__chunks {
  margin-top: 24px;
}

.document-detail__chunks-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

@media (min-width: 640px) {
  .document-detail__chunks-header {
    flex-direction: row;
    align-items: baseline;
    justify-content: space-between;
  }
}

.chunk-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chunk-list__item details {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
  padding: 16px;
}

.chunk-list__item summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  gap: 12px;
  font-weight: 600;
}

.chunk-list__item summary::-webkit-details-marker {
  display: none;
}

.chunk-list__item pre {
  margin-top: 12px;
  background: #ffffff;
  border-radius: 8px;
  padding: 12px;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.chunk-list__meta {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.chunk-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-pagination__label {
  font-size: 13px;
  color: #6b7280;
}

.chunk-pagination__select,
.document-detail__pager-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
  background: #ffffff;
}

.document-detail__source details {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 20px;
  background: #f9fafb;
}

.document-content__summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  cursor: pointer;
}

.document-content__summary-range {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.document-detail__source-body {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
}

.document-detail__loading-text,
.document-detail__error {
  margin: 0;
  color: #6b7280;
}

.document-detail__error {
  color: #dc2626;
}

.document-detail__pager {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.document-detail__pager-label {
  font-size: 13px;
  color: #6b7280;
}

.document-detail__pager--footer {
  justify-content: space-between;
}

.document-detail__pager-actions {
  display: flex;
  gap: 8px;
}

.document-detail__pager-button {
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  background: #e5e7eb;
  cursor: pointer;
  font-weight: 600;
}

.document-detail__pager-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.document-content__text {
  list-style: decimal;
  margin: 0;
  padding-left: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  max-height: 360px;
  overflow: auto;
}

.document-content__text li {
  padding: 6px 12px;
  border-bottom: 1px solid #f3f4f6;
  white-space: pre-wrap;
  word-break: break-word;
}

.document-content__text li:last-child {
  border-bottom: none;
}

.document-content__table-wrapper {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow-x: auto;
  width: 100%;
  max-width: 100%;
}

.document-content__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 480px;
  background: #ffffff;
}

.document-content__table th,
.document-content__table td {
  border-bottom: 1px solid #f3f4f6;
}

.document-content__index-header {
  width: 56px;
  text-align: center;
  font-weight: 600;
  background: #f3f4f6;
  position: sticky;
  left: 0;
  z-index: 1;
}

.document-content__index-cell {
  text-align: center;
  font-weight: 600;
  background: #f9fafb;
  position: sticky;
  left: 0;
  z-index: 1;
}

.document-content__cell {
  min-width: 160px;
}

.document-content__cell-button {
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 12px;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-radius: 6px;
}

.document-content__cell-button:hover,
.document-content__cell-button:focus {
  background: #eef2ff;
  outline: none;
}

.document-content__summary-helper {
  font-size: 13px;
  color: #6b7280;
}

.document-content__preview-meta {
  margin: 0 0 12px;
  font-size: 14px;
  color: #4b5563;
}

.document-content__preview-value {
  max-height: 400px;
  overflow: auto;
  background: #f3f4f6;
  padding: 16px;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 640px) {
  .document-detail__pager--footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .document-detail__pager-actions {
    width: 100%;
  }

  .document-detail__pager-actions .document-detail__pager-button {
    flex: 1;
  }
}

.document-detail__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 320px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  color: #6b7280;
}

.button {
  border: none;
  border-radius: 8px;
  padding: 12px 18px;
  font-weight: 600;
  cursor: pointer;
  font-size: 15px;
}

.button--primary {
  background: #1f2937;
  color: #ffffff;
}

.button--danger {
  background: #ef4444;
  color: #ffffff;
}
</style>
