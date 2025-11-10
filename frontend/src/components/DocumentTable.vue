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
          <td colspan="5" class="empty">No documents found.</td>
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
            <div v-if="document.isUploading" class="uploading">
              <span>{{ document.isCancelling ? '正在取消…' : '正在上传…' }}</span>
              <button
                v-if="!document.isCancelling"
                class="uploading__cancel"
                type="button"
                @click="requestCancel(document)"
              >
                取消
              </button>
            </div>
            <RouterLink
              v-else
              :to="{ name: 'document-detail', params: { id: document.uuid } }"
              >View</RouterLink
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router';

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

const emit = defineEmits(['update:sort', 'cancel-upload']);

const columns = [
  { key: 'title', label: 'Name', sortable: true },
  { key: 'domain', label: 'Domain', sortable: true },
  { key: 'created_at', label: 'Created', sortable: true },
  { key: 'updated_at', label: 'Updated', sortable: true }
];

function changeSort(key) {
  let direction = 'asc';
  if (props.sortBy === key) {
    direction = props.sortDirection === 'asc' ? 'desc' : 'asc';
  }
  emit('update:sort', { sortBy: key, sortDirection: direction });
}

function requestCancel(document) {
  if (!document?.tempId) return;
  emit('cancel-upload', document.tempId);
}

function resolveDomainName(domainId) {
  if (!domainId) return '—';
  const domain = props.domains.find((item) => item.id === domainId);
  return domain?.name || `Domain #${domainId}`;
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString();
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
  min-width: 120px;
}

.actions a {
  color: #1f2937;
  font-weight: 600;
  text-decoration: none;
}

.uploading {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #2563eb;
  font-weight: 600;
}

.uploading__cancel {
  border: none;
  background: transparent;
  color: #ef4444;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.uploading__cancel:hover {
  text-decoration: underline;
}
</style>
