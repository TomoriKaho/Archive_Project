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
      <table>
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
          <template v-for="(archive, index) in archives" :key="`${archive.id || archive.externalId || index}`">
            <tr class="archive-row" @click="toggleExpanded(index)">
              <td>{{ archive.page || index + 1 }}</td>
              <td>{{ archive.archiveName || archive.archive_name || '—' }}</td>
              <td>{{ archive.documentName || archive.document_name || '—' }}</td>
              <td>{{ archive.domainName || archive.domain_name || '—' }}</td>
              <td class="archive-row__cta">
                <span>{{ expanded.has(index) ? uiTexts.collapse : uiTexts.expand }}</span>
                <span aria-hidden="true">{{ expanded.has(index) ? '▴' : '▾' }}</span>
              </td>
            </tr>
            <tr v-if="expanded.has(index)" class="archive-details">
              <td :colspan="5">
                <div class="archive-details__content">
                  <pre v-if="!hasMetadata(archive)" class="archive-details__fallback">{{ formatFallback(archive) }}</pre>
                  <div v-else class="archive-tree">
                    <dl class="archive-tree__list">
                      <template v-for="(value, key) in archive.metadata" :key="key">
                        <div class="archive-tree__item">
                          <dt>{{ key }}</dt>
                          <dd>
                            <ArchiveTreeNode :value="value" />
                          </dd>
                        </div>
                      </template>
                    </dl>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

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
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue';

import ArchiveTreeNode from './ArchiveTreeNode.vue';

const props = defineProps({
  archives: {
    type: Array,
    default: () => []
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

const expanded = reactive(new Set());

const defaultTexts = {
  placeholder: '搜索结果在这里显示',
  loading: '正在加载…',
  error: '加载失败，请稍后重试',
  empty: '暂无搜索结果',
  collapse: '收起',
  expand: '展开',
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

const totalPages = computed(() => {
  const safeTotal = Number.isFinite(props.total) ? props.total : 0;
  const safeSize = props.pageSize > 0 ? props.pageSize : 10;
  if (!safeTotal || !safeSize) return 1;
  return Math.max(Math.ceil(safeTotal / safeSize), 1);
});

function toggleExpanded(index) {
  if (expanded.has(index)) {
    expanded.delete(index);
  } else {
    expanded.add(index);
  }
}

function hasMetadata(archive) {
  return archive && archive.metadata && typeof archive.metadata === 'object';
}

function formatFallback(archive) {
  if (!archive) return '';
  try {
    return JSON.stringify(archive, null, 2);
  } catch (error) {
    return String(archive);
  }
}
</script>

<style scoped lang="scss">
.archive-table {
  width: 100%;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.archive-table__body table {
  width: 100%;
  border-collapse: collapse;
}

.archive-table__body th,
.archive-table__body td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
}

.archive-row {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.archive-row:hover {
  background: #f8fbff;
}

.archive-row__cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-weight: 600;
}

.archive-details td {
  background: linear-gradient(180deg, #f9fbff, #ffffff);
}

.archive-details__content {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.06);
}

.archive-details__fallback {
  margin: 0;
  white-space: pre-wrap;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  color: #1f2937;
}

.archive-tree__list {
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 14px;
}

.archive-tree__item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
}

.archive-tree__item dt {
  margin: 0 0 6px;
  font-weight: 700;
  color: #0f172a;
}

.archive-tree__item dd {
  margin: 0;
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
</style>
