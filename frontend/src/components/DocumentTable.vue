<template>
  <div class="document-table">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">
            <button
              v-if="column.sortable"
              type="button"
              @click="changeSort(column.key)"
            >
              {{ column.label }}
              <span v-if="sortBy === column.key">{{
                sortDirection === 'asc' ? '▲' : '▼'
              }}</span>
            </button>
            <span v-else>{{ column.label }}</span>
          </th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="documents.length === 0">
          <td :colspan="columns.length + 1" class="empty">
            {{ t('documents.table.empty') }}
          </td>
        </tr>
        <tr v-for="document in documents" :key="document.id || document.tempId">
          <td v-for="column in columns" :key="column.key">
            <template v-if="column.key === 'title'">
              {{ document.title }}
            </template>
            <template v-else-if="column.key === 'domain'">
              {{ resolveDomainName(document.domain_id) }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDate(document.created_at) }}
            </template>
            <template v-else-if="column.key === 'updated_at'">
              {{ formatDate(document.updated_at) }}
            </template>
          </td>
          <td class="actions">
            <span v-if="document.isUploading" class="uploading">
              {{ t('documents.uploading') }}
            </span>
            <template v-else>
              <RouterLink
                :to="{ name: 'document-detail', params: { id: document.uuid } }"
                >{{ t('common.view') }}</RouterLink
              >
              <span v-if="progressText(document)" class="progress">
                {{ progressText(document) }}
              </span>
              <button
                v-if="canCancel(document)"
                type="button"
                class="cancel-button"
                :disabled="document._isCancelling"
                @click="requestCancel(document)"
              >
                {{
                  document._isCancelling
                    ? t('documents.table.cancelling')
                    : t('documents.table.cancel')
                }}
              </button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router';

import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  documents: {
    type: Array,
    default: () => []
  },
  domains: {
    type: Array,
    default: () => []
  },
  sortBy: {
    type: String,
    default: 'created_at'
  },
  sortDirection: {
    type: String,
    default: 'desc'
  }
});

const emit = defineEmits(['update:sort', 'cancel-indexing']);

const { t, locale } = useI18n();

const columns = computed(() => [
  { key: 'title', label: t('documents.table.columns.name'), sortable: true },
  { key: 'domain', label: t('documents.table.columns.domain'), sortable: true },
  {
    key: 'created_at',
    label: t('documents.table.columns.created'),
    sortable: true
  },
  {
    key: 'updated_at',
    label: t('documents.table.columns.updated'),
    sortable: true
  }
]);

function changeSort(key) {
  let direction = 'asc';
  if (props.sortBy === key) {
    direction = props.sortDirection === 'asc' ? 'desc' : 'asc';
  }
  emit('update:sort', { sortBy: key, sortDirection: direction });
}

function resolveDomainName(domainId) {
  if (!domainId) return '—';
  const domain = props.domains.find((item) => item.id === domainId);
  return domain?.name || t('documents.unknownDomain', { id: domainId });
}

function canCancel(document) {
  if (!document || document.isUploading) return false;
  if (!document.id) return false;
  const status = document.vector_index_status;
  return ['queued', 'processing', 'pending'].includes(status);
}

function requestCancel(document) {
  emit('cancel-indexing', document);
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(locale.value);
  } catch (error) {
    return new Date(value).toLocaleDateString();
  }
}

function progressText(document) {
  if (!document) return '';

  const status = document.vector_index_status;
  const total = Number(document.vector_total_chunks ?? 0);
  const indexed = Number(document.vector_indexed_chunks ?? 0);

  if (!status) {
    return '';
  }

  if (status === 'failed') {
    return t('documents.table.progress.failed');
  }

  const safeTotal = Number.isNaN(total) ? 0 : Math.max(0, Math.floor(total));
  const safeIndexed = Number.isNaN(indexed) ? 0 : Math.max(0, Math.floor(indexed));

  if (safeTotal === 0) {
    return status === 'completed'
      ? t('documents.table.progress.completedNoChunks')
      : t('documents.table.progress.empty');
  }

  const clampedIndexed = Math.min(safeIndexed, safeTotal);
  let percent = Math.floor((clampedIndexed / safeTotal) * 100);
  if (status === 'completed') {
    percent = 100;
  }

  const statusKey = `documents.table.progress.status.${status}`;
  const translatedStatus = t(statusKey);
  const statusLabel = translatedStatus === statusKey ? status : translatedStatus;
  return t('documents.table.progress.summary', {
    status: statusLabel,
    indexed: clampedIndexed,
    total: safeTotal,
    percent
  });
}

</script>

<style scoped>
.document-table table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

th,
td {
  padding: 16px 20px;
  text-align: left;
  border-bottom: 1px solid #f3f4f6;
}

th button {
  background: transparent;
  border: none;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 32px 16px;
}

.actions {
  min-width: 160px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.actions a {
  color: #1f2937;
  font-weight: 600;
  text-decoration: none;
}

.actions .progress {
  color: #6b7280;
  font-size: 0.875rem;
}

.cancel-button {
  padding: 6px 12px;
  border: 1px solid #f87171;
  background: transparent;
  color: #dc2626;
  border-radius: 9999px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.cancel-button:hover:enabled {
  background: #fee2e2;
}

.cancel-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.uploading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-weight: 600;
}
</style>
