<template>
  <div class="archive-table">
    <div v-if="state === 'idle'" class="archive-table__placeholder">
      <slot name="placeholder">{{ uiTexts.placeholder }}</slot>
    </div>
    <div v-else-if="state === 'loading'" class="archive-table__placeholder">
      {{ uiTexts.loading }}
    </div>
    <div v-else-if="state === 'error'" class="archive-table__placeholder archive-table__placeholder--error">
      {{ errorMessage || uiTexts.error }}
    </div>
    <div v-else-if="!archives.length" class="archive-table__placeholder">
      {{ uiTexts.empty }}
    </div>
    <div v-else class="archive-table__body">
      <div class="archive-table__scroll">
        <table class="archive-table__grid">
          <colgroup>
            <col style="width: 90px" />
            <col style="width: 220px" />
            <col style="width: 240px" />
            <col style="width: 160px" />
            <col style="width: 140px" />
          </colgroup>
          <thead>
            <tr>
              <th>{{ uiTexts.columns.index }}</th>
              <th>{{ uiTexts.columns.archive }}</th>
              <th>{{ uiTexts.columns.document }}</th>
              <th>{{ uiTexts.columns.domain }}</th>
              <th>{{ uiTexts.columns.detail }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(archive, index) in archives"
              :key="`${archive.id || archive.externalId || index}`"
              class="archive-row"
            >
              <td>
                <button class="archive-cell" type="button" @click="openDetails(archive, index)">
                  <span class="archive-cell__text">{{ resolveIndex(archive, index) }}</span>
                </button>
              </td>
              <td>
                <button class="archive-cell" type="button" @click="openDetails(archive, index)">
                  <span class="archive-cell__text" :title="resolveArchiveName(archive)">
                    {{ truncateText(resolveArchiveName(archive)) }}
                  </span>
                </button>
              </td>
              <td>
                <button class="archive-cell" type="button" @click="openDetails(archive, index)">
                  <span class="archive-cell__text" :title="resolveDocumentName(archive)">
                    {{ truncateText(resolveDocumentName(archive)) }}
                  </span>
                </button>
              </td>
              <td>
                <button class="archive-cell" type="button" @click="openDetails(archive, index)">
                  <span class="archive-cell__text" :title="resolveDomainName(archive)">
                    {{ truncateText(resolveDomainName(archive)) }}
                  </span>
                </button>
              </td>
              <td>
                <button class="archive-cell archive-cell--cta" type="button" @click="openDetails(archive, index)">
                  <span>{{ uiTexts.view }}</span>
                  <span aria-hidden="true">▸</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalPages > 1" class="archive-table__pagination">
        <button
          class="archive-table__pager"
          type="button"
          :disabled="page <= 1"
          @click="$emit('update:page', page - 1)"
        >
          {{ uiTexts.previous }}
        </button>
        <span class="archive-table__page-indicator">{{ page }} / {{ totalPages }}</span>
        <button
          class="archive-table__pager"
          type="button"
          :disabled="page >= totalPages"
          @click="$emit('update:page', page + 1)"
        >
          {{ uiTexts.next }}
        </button>
      </div>
    </div>

    <BaseModal v-model="isDetailOpen" :title="detailTitle" :close-on-overlay="false">
      <div v-if="activeArchive" class="archive-detail">
        <section class="archive-detail__summary">
          <div class="archive-detail__summary-item">
            <span class="archive-detail__label">{{ uiTexts.columns.archive }}</span>
            <HighlightedText
              class="archive-detail__summary-text"
              :text="resolveArchiveName(activeArchive)"
              :tokens="highlightTokens"
            />
          </div>
          <div class="archive-detail__summary-item">
            <span class="archive-detail__label">{{ uiTexts.columns.document }}</span>
            <HighlightedText
              class="archive-detail__summary-text"
              :text="resolveDocumentName(activeArchive)"
              :tokens="highlightTokens"
            />
          </div>
          <div class="archive-detail__summary-item">
            <span class="archive-detail__label">{{ uiTexts.columns.domain }}</span>
            <HighlightedText
              class="archive-detail__summary-text"
              :text="resolveDomainName(activeArchive)"
              :tokens="highlightTokens"
            />
          </div>
        </section>

        <section class="archive-detail__metadata">
          <header class="archive-detail__metadata-header">
            <h4>{{ uiTexts.metadata }}</h4>
            <span class="archive-detail__hint" v-if="!hasMetadataEntries">
              {{ uiTexts.noMetadata }}
            </span>
          </header>
          <div v-if="hasMetadataEntries" class="archive-tree">
            <dl v-if="detailEntries.length" class="archive-tree__list">
              <template v-for="([key, value], index) in detailEntries" :key="`${key}-${index}`">
                <div class="archive-tree__item">
                  <dt>
                    <HighlightedText class="archive-detail__text" :text="key" :tokens="highlightTokens" />
                  </dt>
                  <dd>
                    <ArchiveTreeCellRenderer
                      v-if="isArchiveTreeValue(value)"
                      :value="value"
                      :expand-label="uiTexts.expandDetails"
                      :empty-text="uiTexts.emptyCell"
                    />
                    <StructuredViewer v-else-if="isStructuredRenderable(value)" :value="value" />
                    <HighlightedText
                      v-else
                      class="archive-detail__text"
                      :text="formatStructuredFallback(value, uiTexts.emptyCell)"
                      :tokens="highlightTokens"
                    />
                  </dd>
                </div>
              </template>
            </dl>
          </div>
          <pre v-else class="archive-details__fallback">{{ formatFallback(activeArchive) }}</pre>
        </section>
      </div>

      <template #footer>
        <button class="archive-table__close" type="button" @click="isDetailOpen = false">
          {{ uiTexts.close }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, ref, useAttrs } from 'vue';

import {
  ArchiveTreeCellRenderer,
  StructuredViewer,
  formatStructuredFallback,
  hasArchiveText,
  isObjectLike,
  isArchiveTreeValue,
  isStructuredRenderable,
  parseStructuredValue
} from '../../../frontend_shared/components/structured';

import BaseModal from './BaseModal.vue';

const props = defineProps({
  archives: {
    type: Array,
    default: () => []
  },
  searchQuery: {
    type: String,
    default: ''
  },
  searchType: {
    type: String,
    default: 'precise'
  },
  page: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  },
  total: {
    type: Number,
    default: 0
  },
  state: {
    type: String,
    default: 'idle'
  },
  errorMessage: {
    type: String,
    default: ''
  },
  texts: {
    type: Object,
    default: () => ({})
  }
});

defineEmits(['update:page']);

const activeArchive = ref(null);
const isDetailOpen = ref(false);

const HighlightedText = defineComponent({
  name: 'HighlightedText',
  props: {
    text: {
      type: [String, Number, Boolean],
      default: ''
    },
    tokens: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const attrs = useAttrs();
    const matcher = computed(() => buildMatcher(props.tokens));

    function buildMatcher(tokens = []) {
      const normalized = tokens
        .map((token) => (token === null || token === undefined ? '' : String(token).trim()))
        .filter(Boolean);
      if (!normalized.length) return null;
      return new RegExp(`(${normalized.map((token) => escapeRegExp(token)).join('|')})`, 'gi');
    }

    function escapeRegExp(text) {
      return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    return () => {
      const content = props.text === null || props.text === undefined ? '' : String(props.text);
      const highlightMatcher = matcher.value;

      const baseProps = { ...attrs, class: ['archive-highlight-text', attrs.class] };

      if (!content || !highlightMatcher) {
        return h('span', baseProps, content);
      }

      const segmentMatcher = new RegExp(highlightMatcher.source, 'gi');
      const strictMatcher = new RegExp(`^${highlightMatcher.source}$`, 'i');
      const segments = content.split(segmentMatcher);

      return h(
        'span',
        baseProps,
        segments
          .filter((part) => part !== '')
          .map((part, index) =>
            strictMatcher.test(part)
              ? h('mark', { class: 'archive-highlight', key: `mark-${index}` }, part)
              : h('span', { key: `text-${index}` }, part)
          )
      );
    };
  }
});

const defaultTexts = {
  placeholder: '搜索结果在这里显示',
  loading: '正在加载…',
  error: '加载失败，请稍后重试',
  empty: '暂无搜索结果',
  view: '查看',
  close: '关闭',
  metadata: '档案元数据',
  noMetadata: '暂无可展示的元数据',
  expandDetails: '展开',
  emptyCell: '—',
  previous: '上一页',
  next: '下一页',
  columns: {
    index: '页序号',
    archive: '档案名称',
    document: '文档名称',
    domain: '知识域',
    detail: '详细内容'
  }
};

const uiTexts = computed(() => ({
  ...defaultTexts,
  ...(props.texts || {}),
  columns: {
    ...defaultTexts.columns,
    ...(props.texts?.columns || {})
  }
}));

const highlightTokens = computed(() => {
  const query = (props.searchQuery || '').trim();
  if (!query) return [];

  if (props.searchType === 'fuzzy') {
    return query
      .split(/[\s,，。；;、]+/)
      .map((token) => token.trim())
      .filter(Boolean);
  }

  return [query];
});

const totalPages = computed(() => {
  const safeTotal = Number.isFinite(props.total) ? props.total : 0;
  const safeSize = props.pageSize > 0 ? props.pageSize : 10;
  if (!safeTotal || !safeSize) return 1;
  return Math.max(Math.ceil(safeTotal / safeSize), 1);
});

const detailTitle = computed(() => {
  if (!activeArchive.value) return uiTexts.value.metadata;
  return `${uiTexts.value.columns.archive}：${resolveArchiveName(activeArchive.value)}`;
});

const detailEntries = computed(() => {
  const metadata = parseStructuredValue(activeArchive.value?.metadata);

  if (isObjectLike(metadata)) return Object.entries(metadata);
  if (Array.isArray(metadata) && metadata.length) return [['内容', metadata]];
  if (hasArchiveText(metadata)) return [['内容', metadata]];

  return [];
});

const hasMetadataEntries = computed(() => detailEntries.value.length > 0);

function openDetails(archive) {
  activeArchive.value = archive;
  isDetailOpen.value = true;
}

function formatFallback(archive) {
  if (!archive) return '';
  try {
    return JSON.stringify(archive, null, 2);
  } catch (error) {
    return String(archive);
  }
}

function resolveIndex(archive, index) {
  if (archive && archive.page) return archive.page;
  return index + 1;
}

function resolveArchiveName(archive) {
  return archive?.archiveName || archive?.archive_name || '—';
}

function resolveDocumentName(archive) {
  return archive?.documentName || archive?.document_name || '—';
}

function resolveDomainName(archive) {
  return archive?.domainName || archive?.domain_name || '—';
}

function truncateText(text, maxLength = 22) {
  if (!text || typeof text !== 'string') return text;
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}…`;
}
</script>

<style scoped lang="scss">
.archive-table {
  width: 100%;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.archive-table__body {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.archive-table__scroll {
  flex: 1 1 auto;
  overflow: auto;
}

.archive-table__grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  border: 1px solid #e5e7eb;
  min-width: 800px;
}

.archive-table__body th,
.archive-table__body td {
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  text-align: left;
  white-space: nowrap;
  background: #ffffff;
}

.archive-table__body th {
  font-weight: 700;
  color: #0f172a;
  background: linear-gradient(180deg, #f9fafb, #eff3ff);
}

.archive-row {
  transition: background-color 0.2s ease;
}

.archive-row:hover {
  background: #f8fbff;
}

.archive-cell {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.archive-cell__text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.archive-cell--cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-weight: 700;
}

.archive-details__fallback {
  margin: 0;
  white-space: pre-wrap;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  color: #1f2937;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
}

.archive-tree__list {
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.archive-tree__item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
}

.archive-tree__item:hover {
  border-color: #c7d2fe;
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.08);
}

.archive-tree__item dt {
  margin: 0 0 6px;
  font-weight: 700;
  color: #0f172a;
}

.archive-tree__item dd {
  margin: 0;
}

.archive-tree {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.archive-tree__node {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.archive-tree__header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.archive-tree__title {
  margin: 0;
  font-weight: 700;
  color: #0f172a;
}

.archive-tree__meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  color: #475569;
  font-size: 0.92rem;
}

.archive-tree__meta-item {
  background: #e0f2fe;
  color: #0369a1;
  padding: 4px 8px;
  border-radius: 999px;
}

.archive-tree__scope {
  margin-top: 8px;
}

.archive-tree__scope-summary {
  cursor: pointer;
  color: #2563eb;
  font-weight: 600;
}

.archive-tree__scope-body {
  margin-top: 6px;
  color: #1f2937;
  white-space: pre-wrap;
}

.archive-tree--empty {
  color: #94a3b8;
}

.archive-table__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px;
  background: #f8fafc;
}

.archive-table__pager {
  border: none;
  background: #2563eb;
  color: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.18);
}

.archive-table__pager:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.archive-table__page-indicator {
  color: #475569;
  font-weight: 600;
}

.archive-table__placeholder {
  padding: 24px;
  text-align: center;
  color: #64748b;
}

.archive-table__placeholder--error {
  color: #dc2626;
}

.archive-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.archive-detail__summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 16px;
}

.archive-detail__summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.archive-detail__label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 600;
}

.archive-detail__summary-text {
  color: #0f172a;
  font-weight: 700;
}

.archive-detail__text {
  white-space: pre-line;
}

.archive-detail__metadata {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.archive-detail__metadata-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.archive-detail__metadata-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.archive-detail__hint {
  color: #6b7280;
  font-size: 13px;
}

.archive-table__close {
  border: none;
  background: #111827;
  color: #ffffff;
  padding: 10px 16px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}

.archive-table__close:hover {
  background: #1f2937;
}

.archive-highlight-text {
  display: inline;
}

.archive-highlight {
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 4px;
  padding: 0 2px;
}
</style>
