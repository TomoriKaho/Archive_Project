<template>
  <section v-if="document" class="document-detail">
    <header class="document-detail__header">
      <div>
        <h2>{{ document.title }}</h2>
        <p>{{ t('documentDetail.domainLabel', { name: domainName }) }}</p>
      </div>
      <div class="document-detail__actions">
        <button class="button" type="button" @click="openEdit">
          {{ t('common.edit') }}
        </button>
        <button class="button button--danger" type="button" @click="openDelete">
          {{ t('common.delete') }}
        </button>
      </div>
    </header>

    <div class="document-detail__meta">
      <div>
        <span class="label">{{ t('documentDetail.meta.created') }}</span>
        <span>{{ formatDate(document.created_at) }}</span>
      </div>
      <div>
        <span class="label">{{ t('documentDetail.meta.updated') }}</span>
        <span>{{ formatDate(document.updated_at) }}</span>
      </div>
      <div>
        <span class="label">{{ t('documentDetail.meta.uuid') }}</span>
        <span class="mono">{{ document.uuid }}</span>
      </div>
      <div>
        <span class="label">{{ t('documentDetail.meta.domainId') }}</span>
        <span>{{ document.domain_id }}</span>
      </div>
    </div>

    <article class="document-detail__content document-detail__source">
      <details @toggle="onContentToggle" :open="isContentExpanded">
        <summary class="document-content__summary">
          <span>{{ t('documentDetail.content.title') }}</span>
          <span v-if="contentRangeLabel" class="document-content__summary-range">
            {{ contentRangeLabel }}
          </span>
        </summary>
        <div class="document-detail__source-body">
          <p v-if="contentError" class="document-detail__error">{{ contentError }}</p>
          <p v-else-if="isContentLoading" class="document-detail__loading-text">
            {{ t('documentDetail.content.loading') }}
          </p>
          <template v-else>
            <p
              v-if="contentPage && !contentItems.length"
              class="document-detail__empty"
            >
              {{ t('documentDetail.content.empty') }}
            </p>
            <template v-else>
              <div
                v-if="contentPage && contentPageOptions.length"
                class="document-detail__pager"
              >
                <label class="document-detail__pager-label" for="content-page-select"
                  >{{ t('documentDetail.content.rangeLabel') }}</label
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
                v-else-if="contentPage && ['csv', 'json'].includes(contentPage.mode) && normalizedRows.length"
                ref="tableWrapperRef"
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
              {{
                t('documentDetail.content.total', {
                  total: contentPage.total,
                  unit: getContentUnit(contentPage.mode)
                })
              }}
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
                {{ t('common.previous') }}
              </button>
              <button
                class="document-detail__pager-button"
                type="button"
                :disabled="contentPageIndex >= contentPageOptions.length - 1"
                @click="loadNextContentPage"
              >
                {{ t('common.next') }}
              </button>
            </div>
          </div>
        </div>
      </details>
    </article>

    <article class="document-detail__content document-detail__chunks">
      <header class="document-detail__chunks-header">
        <div>
          <h3>{{ t('documentDetail.chunks.title') }}</h3>
          <span class="document-detail__hint">
            {{ chunkSummaryText }}
            <template v-if="chunkRangeLabel">
              {{ t('documentDetail.chunks.currentRange', { range: chunkRangeLabel }) }}
            </template>
          </span>
        </div>
        <div v-if="chunkPageOptions.length > 1" class="chunk-pagination">
          <label class="chunk-pagination__label" for="chunk-page-select"
            >{{ t('documentDetail.chunks.rangeLabel') }}</label
          >
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
      <p v-if="isLoadingChunks" class="document-detail__empty">
        {{ t('documentDetail.chunks.loading') }}
      </p>
      <p v-else-if="!hasChunks" class="document-detail__empty">
        {{ t('documentDetail.chunks.empty') }}
      </p>
      <p v-else-if="!visibleChunks.length" class="document-detail__empty">
        {{ t('documentDetail.chunks.loading') }}
      </p>
      <ul v-else class="chunk-list">
        <li v-for="chunk in visibleChunks" :key="chunk.id" class="chunk-list__item">
          <details>
            <summary>
              <span>
                {{
                  t('documentDetail.chunks.itemTitle', {
                    index: chunk.ordinal + 1,
                    id: chunk.id
                  })
                }}
              </span>
              <span class="chunk-list__meta">
                {{ t('documentDetail.chunks.length', { count: formatChunkLength(chunk) }) }}
              </span>
            </summary>
            <pre>{{ chunk.content }}</pre>
          </details>
        </li>
      </ul>
    </article>
    <BaseModal
      v-model="isPreviewOpen"
      :title="t('documentDetail.preview.title')"
      :close-on-overlay="false"
    >
      <p class="document-content__preview-meta">
        {{
          t('documentDetail.preview.meta', {
            row: previewContent.rowNumber,
            header: previewContent.header
          })
        }}
      </p>
      <pre class="document-content__preview-value">{{ previewContent.value }}</pre>
      <template #footer>
        <button class="button" type="button" @click="closePreview">
          {{ t('common.close') }}
        </button>
      </template>
    </BaseModal>

    <BaseModal v-model="isEditOpen" :title="t('documentDetail.edit.title')">
      <div class="tab-pane">
        <div
          class="form-field"
          :class="{ 'form-field--error': editErrors.title }"
        >
          <label for="edit-title">{{ t('documents.form.titleLabel') }}</label>
          <input id="edit-title" v-model.trim="editForm.title" type="text" />
          <p v-if="editErrors.title" class="form-field__error">
            {{ editErrors.title }}
          </p>
        </div>
      </div>
      <template #footer>
        <button class="button" type="button" @click="closeEdit">
          {{ t('common.cancel') }}
        </button>
        <button class="button button--primary" type="button" @click="save">
          {{ isSaving ? t('common.saving') : t('documentDetail.edit.save') }}
        </button>
      </template>
    </BaseModal>
    <BaseModal v-model="isDeleteOpen" :title="t('documentDetail.delete.title')">
      <p>{{ t('documentDetail.delete.message') }}</p>
      <template #footer>
        <button class="button" type="button" @click="closeDelete">
          {{ t('common.cancel') }}
        </button>
        <button
          class="button button--danger"
          type="button"
          :disabled="isDeleting"
          @click="remove"
        >
          {{ isDeleting ? t('common.deleting') : t('documentDetail.delete.confirm') }}
        </button>
      </template>
    </BaseModal>
  </section>
  <section v-else-if="loadError" class="document-detail__error-state">
    {{ loadError }}
  </section>
  <section v-else class="document-detail__loading">
    {{ t('documentDetail.loadingDocument') }}
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

import BaseModal from '@/components/BaseModal.vue';
import { useDocumentsStore } from '@/store/documents';
import { useDomainsStore } from '@/store/domains';

const route = useRoute();
const router = useRouter();
const documentsStore = useDocumentsStore();
const domainsStore = useDomainsStore();
const { t, locale } = useI18n();

const isEditOpen = ref(false);
const isDeleteOpen = ref(false);
const isDeleting = ref(false);
const isSaving = ref(false);

const chunkPageSize = 100;
const CELL_PREVIEW_LENGTH = 60;
const DEFAULT_CSV_LIMIT = 10;
const DEFAULT_TEXT_LIMIT = 100;
const chunkPageIndex = ref(0);
const contentPageIndex = ref(0);
const isContentExpanded = ref(false);
const contentError = ref('');
const loadError = ref('');
const isPreviewOpen = ref(false);
const previewContent = reactive({
  header: '',
  value: '',
  rowNumber: 0
});
const tableWrapperRef = ref(null);
const isTableScrollable = ref(false);
let tableWrapperResizeObserver = null;
let tableResizeObserver = null;

function disconnectTableObservers() {
  if (tableWrapperResizeObserver) {
    tableWrapperResizeObserver.disconnect();
    tableWrapperResizeObserver = null;
  }
  if (tableResizeObserver) {
    tableResizeObserver.disconnect();
    tableResizeObserver = null;
  }
}

function observeTableDimensions(wrapper) {
  if (typeof ResizeObserver === 'undefined' || !wrapper) return;
  const table = wrapper.querySelector('.document-content__table');
  disconnectTableObservers();
  tableWrapperResizeObserver = new ResizeObserver(() => {
    scheduleTableScrollMeasurement();
  });
  tableWrapperResizeObserver.observe(wrapper);
  if (table) {
    tableResizeObserver = new ResizeObserver(() => {
      scheduleTableScrollMeasurement();
    });
    tableResizeObserver.observe(table);
  }
}

function scheduleTableScrollMeasurement() {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(() => {
      updateTableScrollState();
    });
    return;
  }
  updateTableScrollState();
}

const editForm = reactive({
  title: ''
});

const editErrors = reactive({
  title: ''
});

const document = computed(() => documentsStore.activeDocument);
const documentSource = computed(() => document.value?.doc_metadata?.source || 'text');
const isStructuredSource = computed(() => ['csv', 'json'].includes(documentSource.value));
const chunkPage = computed(() => documentsStore.activeChunkPage);
const isLoadingChunks = computed(() => documentsStore.isLoadingChunks);
const chunkTotal = computed(() => {
  const pageTotal = chunkPage.value?.total;
  if (typeof pageTotal === 'number' && pageTotal >= 0) {
    return pageTotal;
  }
  const docTotal = document.value?.vector_total_chunks;
  if (typeof docTotal === 'number' && docTotal >= 0) {
    return docTotal;
  }
  return 0;
});
const chunkSummaryText = computed(() =>
  t('documentDetail.chunks.summary', { count: chunkTotal.value })
);
const contentPage = computed(() => documentsStore.activeContent);
const isContentLoading = computed(() => documentsStore.isLoadingContent);
const domainName = computed(() => {
  const domain = domainsStore.items.find(
    (item) => item.id === document.value?.domain_id
  );
  if (!document.value) return '—';
  return domain?.name || t('documents.unknownDomain', { id: document.value.domain_id });
});

function resolveContentLimit(page, fallbackLimit) {
  const defaultFallback = isStructuredSource.value
    ? DEFAULT_CSV_LIMIT
    : DEFAULT_TEXT_LIMIT;
  const fallback = typeof fallbackLimit === 'number' && fallbackLimit > 0
    ? fallbackLimit
    : defaultFallback;
  if (!page) {
    return fallback;
  }
  const rawLimit = page.limit && page.limit > 0 ? page.limit : fallback;
  if (page.mode === 'csv' || page.mode === 'json') {
    return Math.min(rawLimit, DEFAULT_CSV_LIMIT);
  }
  if (page.mode === 'text') {
    return rawLimit;
  }
  if (isStructuredSource.value) {
    return Math.min(rawLimit, DEFAULT_CSV_LIMIT);
  }
  return rawLimit;
}

const chunkPageOptions = computed(() => {
  const total = chunkTotal.value;
  if (!total) return [];
  const totalPages = Math.ceil(total / chunkPageSize);
  return Array.from({ length: totalPages }, (_, index) => {
    const start = index * chunkPageSize + 1;
    const end = Math.min((index + 1) * chunkPageSize, total);
    return { index, label: `${start}-${end}` };
  });
});

const visibleChunks = computed(() => {
  const items = chunkPage.value?.items;
  if (!Array.isArray(items)) return [];
  return items;
});

const hasChunks = computed(() => chunkTotal.value > 0);

const chunkRangeLabel = computed(() => {
  if (!visibleChunks.value.length || !chunkTotal.value) return '';
  const limit = chunkPage.value?.limit && chunkPage.value.limit > 0
    ? chunkPage.value.limit
    : chunkPageSize;
  const offset = chunkPage.value?.offset ?? chunkPageIndex.value * limit;
  const start = Math.min(offset + 1, Math.max(chunkTotal.value, 1));
  const end = Math.min(offset + visibleChunks.value.length, chunkTotal.value);
  return `${start}-${end} / ${chunkTotal.value}`;
});

function extractRootKey(path) {
  const value = String(path || '');
  if (!value) return '';
  const colonIndex = value.indexOf(':');
  const bracketIndex = value.indexOf('[');
  const cutoff = [colonIndex, bracketIndex]
    .filter((index) => index >= 0)
    .reduce((min, current) => Math.min(min, current), value.length);
  return value.slice(0, cutoff);
}

function parsePathTokens(path) {
  const value = String(path || '');
  if (!value) return [];

  const tokens = [];
  const segments = value.split(':');
  const segmentPattern = /([^\[\]]+)|(\[(\d+)\])/g;

  for (const segment of segments) {
    segmentPattern.lastIndex = 0;
    let match = segmentPattern.exec(segment);
    while (match) {
      if (match[1]) {
        tokens.push(match[1]);
      } else if (match[3]) {
        tokens.push(Number(match[3]));
      }
      match = segmentPattern.exec(segment);
    }
  }

  return tokens;
}

function buildStructuredRow(rawHeaders, row) {
  const result = {};
  const cells = Array.isArray(row) ? row : [row];

  rawHeaders.forEach((path, index) => {
    if (index >= cells.length) return;
    const tokens = parsePathTokens(path);
    if (!tokens.length) return;

    let current = result;
    const value = cells[index];

    tokens.forEach((token, tokenIndex) => {
      const isLast = tokenIndex === tokens.length - 1;
      const nextToken = tokens[tokenIndex + 1];
      const shouldUseArray = typeof nextToken === 'number';

      if (isLast) {
        if (typeof token === 'number') {
          if (Array.isArray(current)) {
            current[token] = value;
          }
        } else if (current && typeof current === 'object') {
          current[token] = value;
        }
        return;
      }

      if (typeof token === 'number') {
        if (!Array.isArray(current)) {
          return;
        }
        if (!current[token] || typeof current[token] !== 'object') {
          current[token] = shouldUseArray ? [] : {};
        }
        current = current[token];
      } else {
        if (!current[token] || typeof current[token] !== 'object') {
          current[token] = shouldUseArray ? [] : {};
        }
        current = current[token];
      }
    });
  });

  return result;
}

function formatStructuredCell(structuredRow, rootKey) {
  if (!structuredRow || !rootKey) return '';
  const value = structuredRow[rootKey];
  if (value === undefined || value === null) return '';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (error) {
      return String(value);
    }
  }
  return String(value);
}

const contentHeaders = computed(() => {
  const page = contentPage.value;
  if (!page) return [];

  if (page.mode === 'json') {
    const rawHeaders = Array.isArray(page.headers) ? page.headers : [];
    const rootHeaders = [];

    for (const path of rawHeaders) {
      const rootKey = extractRootKey(path);
      if (rootKey && !rootHeaders.includes(rootKey)) {
        rootHeaders.push(rootKey);
      }
    }

    if (rootHeaders.length) {
      return rootHeaders;
    }
  }

  const headers = Array.isArray(page.headers) ? page.headers : [];
  if (headers.length) {
    return headers;
  }
  const rows = Array.isArray(page.rows) ? page.rows : [];
  const maxColumns = rows.reduce((max, row) => Math.max(max, row.length), 0);
  if (!maxColumns) return [];
  return Array.from({ length: maxColumns }, (_, index) =>
    t('documentDetail.csv.autoHeader', { index: index + 1 })
  );
});

const normalizedRows = computed(() => {
  const page = contentPage.value;
  if (!page || !['csv', 'json'].includes(page.mode)) return [];
  const headers = contentHeaders.value;
  const targetLength = headers.length || 0;
  const limit = resolveContentLimit(page);
  const rows = Array.isArray(page.rows) ? page.rows : [];
  const limitedRows = limit ? rows.slice(0, limit) : rows;

  if (page.mode === 'json') {
    const rawHeaders = Array.isArray(page.headers) ? page.headers : [];
    if (!rawHeaders.length || !headers.length) {
      return limitedRows;
    }

    return limitedRows.map((row) => {
      const structuredRow = buildStructuredRow(rawHeaders, row);
      return headers.map((headerKey) => formatStructuredCell(structuredRow, headerKey));
    });
  }

  if (!targetLength) {
    return limitedRows;
  }
  return limitedRows.map((row) => {
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
  if (page.mode === 'csv' || page.mode === 'json') {
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
  const count = ['csv', 'json'].includes(page.mode)
    ? normalizedRows.value.length
    : (Array.isArray(page.lines) ? page.lines.length : 0);
  const start = Math.min(page.offset + 1, page.total);
  const end = Math.min(page.offset + count, page.total);
  return `${start}-${end} / ${page.total}`;
});

const contentPageOptions = computed(() => {
  const page = contentPage.value;
  if (!page || !page.total) return [];
  const limit = resolveContentLimit(page);
  if (!limit || page.total <= limit) return [];
  const totalPages = Math.ceil(page.total / limit);
  return Array.from({ length: totalPages }, (_, index) => {
    const start = index * limit + 1;
    const end = Math.min((index + 1) * limit, page.total);
    return { index, label: `${start}-${end}` };
  });
});

let isSyncingChunkPageIndex = false;

async function loadChunkPage(index) {
  if (!document.value) return;
  const safeIndex = Math.max(0, Number.isFinite(index) ? index : 0);
  const offset = safeIndex * chunkPageSize;
  try {
    await documentsStore.loadDocumentChunks({
      documentUuid: document.value.uuid,
      limit: chunkPageSize,
      offset
    });
  } catch (error) {
    // 请求失败时保持当前展示，错误已在 store 内部通过 toast 提示
  }
}

watch(
  chunkPage,
  (page) => {
    isSyncingChunkPageIndex = true;
    if (!page) {
      chunkPageIndex.value = 0;
    } else {
      const limit = page.limit && page.limit > 0 ? page.limit : chunkPageSize;
      const offset = page.offset && page.offset > 0 ? page.offset : 0;
      const derived = limit > 0 ? Math.floor(offset / limit) : 0;
      chunkPageIndex.value = derived;
    }
    isSyncingChunkPageIndex = false;
  },
  { immediate: true }
);

watch(
  () => chunkPageIndex.value,
  (index, previous) => {
    if (isSyncingChunkPageIndex) return;
    if (index === previous) return;
    if (!document.value) return;
    loadChunkPage(index);
  }
);

watch(chunkTotal, (total) => {
  if (!total) {
    isSyncingChunkPageIndex = true;
    chunkPageIndex.value = 0;
    isSyncingChunkPageIndex = false;
    return;
  }
  const maxIndex = Math.max(Math.ceil(total / chunkPageSize) - 1, 0);
  if (chunkPageIndex.value > maxIndex) {
    loadChunkPage(maxIndex);
  }
});

watch(contentPage, (page) => {
  if (!page) {
    contentPageIndex.value = 0;
    isTableScrollable.value = false;
    disconnectTableObservers();
    return;
  }
  const limit = resolveContentLimit(page);
  const derived = limit ? Math.floor((page.offset ?? 0) / limit) : 0;
  contentPageIndex.value = derived;
  contentError.value = '';
  if (!['csv', 'json'].includes(page.mode)) {
    isTableScrollable.value = false;
    disconnectTableObservers();
    return;
  }
  nextTick(() => {
    const wrapper = tableWrapperRef.value;
    if (wrapper) {
      observeTableDimensions(wrapper);
      updateTableScrollState();
    }
  });
});

function updateTableScrollState() {
  const page = contentPage.value;
  const wrapper = tableWrapperRef.value;
  if (!page || !['csv', 'json'].includes(page.mode) || !wrapper) {
    isTableScrollable.value = false;
    return;
  }
  const scrollableWidth = wrapper.scrollWidth;
  const visibleWidth = wrapper.clientWidth;
  const overflowAllowance = 1; // compensate for fractional pixel rounding
  isTableScrollable.value = scrollableWidth - visibleWidth > overflowAllowance;
}

function handleTableWheel(event) {
  if (!isTableScrollable.value) return;
  const wrapper = tableWrapperRef.value;
  if (!wrapper) return;
  const { deltaY, deltaX } = event;
  if (Math.abs(deltaY) <= Math.abs(deltaX) || Math.abs(deltaY) < 1) {
    return;
  }
  const previousScrollLeft = wrapper.scrollLeft;
  wrapper.scrollLeft += deltaY;
  if (wrapper.scrollLeft !== previousScrollLeft) {
    event.preventDefault();
  }
}

watch(
  tableWrapperRef,
  (element, previous) => {
    if (previous) {
      previous.removeEventListener('wheel', handleTableWheel);
    }
    disconnectTableObservers();
    if (!element) {
      isTableScrollable.value = false;
      return;
    }
    element.addEventListener('wheel', handleTableWheel, { passive: false });
    nextTick(() => {
      observeTableDimensions(element);
      updateTableScrollState();
    });
  }
);

watch(
  () => [
    contentPage.value?.mode,
    normalizedRows.value.length,
    contentHeaders.value.length,
    contentPage.value?.offset,
    contentPage.value?.limit
  ],
  () => {
    nextTick(() => {
      if (!['csv', 'json'].includes(contentPage.value?.mode)) {
        disconnectTableObservers();
        isTableScrollable.value = false;
        return;
      }
      const wrapper = tableWrapperRef.value;
      if (wrapper) {
        observeTableDimensions(wrapper);
        updateTableScrollState();
      }
    });
  },
  { immediate: true }
);

watch(
  document,
  async (value, oldValue) => {
    if (!value) {
      documentsStore.resetActiveContent();
      contentPageIndex.value = 0;
      contentError.value = '';
      isContentExpanded.value = false;
      isPreviewOpen.value = false;
      previewContent.header = '';
      previewContent.value = '';
      previewContent.rowNumber = 0;
      isSyncingChunkPageIndex = true;
      chunkPageIndex.value = 0;
      isSyncingChunkPageIndex = false;
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
      loadError.value = '';
      isSyncingChunkPageIndex = true;
      chunkPageIndex.value = 0;
      isSyncingChunkPageIndex = false;
      try {
        await loadChunkPage(0);
      } catch (error) {
        // 错误已在 loadChunkPage 内部处理
      }
    }
  },
  { immediate: false }
);

onMounted(async () => {
  window.addEventListener('resize', updateTableScrollState);
  nextTick(() => {
    if (['csv', 'json'].includes(contentPage.value?.mode)) {
      const wrapper = tableWrapperRef.value;
      if (wrapper) {
        observeTableDimensions(wrapper);
      }
    }
    updateTableScrollState();
  });
  if (!domainsStore.items.length) {
    await domainsStore.loadDomains();
  }
  try {
    await documentsStore.loadDocument(route.params.id);
    loadError.value = '';
  } catch (error) {
    loadError.value = t('documentDetail.loadError');
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateTableScrollState);
  const wrapper = tableWrapperRef.value;
  if (wrapper) {
    wrapper.removeEventListener('wheel', handleTableWheel);
  }
  disconnectTableObservers();
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
  try {
    return new Date(value).toLocaleString(locale.value);
  } catch (error) {
    return new Date(value).toLocaleString();
  }
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

function getContentUnit(mode) {
  return ['csv', 'json'].includes(mode)
    ? t('documentDetail.content.units.rows')
    : t('documentDetail.content.units.lines');
}

async function loadContentPage(index) {
  if (!document.value) return;
  const current = contentPage.value;
  const baseLimit = resolveContentLimit(current);
  const params = {};
  const limitForOffset = baseLimit;
  if (limitForOffset && limitForOffset > 0) {
    params.limit = limitForOffset;
    if (index > 0) {
      params.offset = index * limitForOffset;
    }
  } else if (current?.limit && current.limit > 0 && index > 0) {
    params.offset = index * current.limit;
  }
  contentError.value = '';
  try {
    const data = await documentsStore.loadDocumentContent(document.value.uuid, params);
    const effectiveLimit = resolveContentLimit(data, limitForOffset);
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
    try {
      await documentsStore.loadDocument(route.params.id);
      loadError.value = '';
    } catch (error) {
      loadError.value = t('documentDetail.loadError');
    }
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
  width: 100%;
  max-width: 100%;
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
  max-width: 100%;
  min-width: 0;
}

.document-detail__source {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.document-detail__source details {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
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
  overflow-x: hidden;
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
  overflow-y: hidden;
  width: 100%;
  max-width: 100%;
}

.document-content__table {
  min-width: max(100%, 480px);
  width: max-content;
  border-collapse: collapse;
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

.document-detail__error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 320px;
  background: #fef2f2;
  border-radius: 16px;
  box-shadow: 0 16px 32px rgba(239, 68, 68, 0.1);
  color: #b91c1c;
  text-align: center;
  padding: 0 24px;
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