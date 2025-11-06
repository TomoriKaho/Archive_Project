<template>
  <div class="document-table">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">
            <button type="button" @click="changeSort(column.key)">
              {{ column.label }}
              <span v-if="sortBy === column.key">{{
                sortDirection === 'asc' ? '▲' : '▼'
              }}</span>
            </button>
          </th>
          <th>Tags</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="documents.length === 0">
          <td colspan="6" class="empty">No documents found.</td>
        </tr>
        <tr v-for="document in documents" :key="document.id">
          <td>{{ document.title }}</td>
          <td>{{ formatDate(document.created_at) }}</td>
          <td>{{ document.owner?.name || document.owner?.email || '—' }}</td>
          <td>
            <div class="tag-list">
              <span v-for="tag in document.tags || []" :key="tag" class="tag">{{
                tag
              }}</span>
            </div>
          </td>
          <td>
            <span
              class="status"
              :class="`status--${document.status || 'ready'}`"
            >
              {{ (document.status || 'ready').toUpperCase() }}
            </span>
          </td>
          <td class="actions">
            <RouterLink
              :to="{ name: 'document-detail', params: { id: document.id } }"
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
  sortBy: {
    type: String,
    default: 'created_at'
  },
  sortDirection: {
    type: String,
    default: 'desc'
  }
});

const emit = defineEmits(['update:sort']);

const columns = [
  { key: 'title', label: 'Name' },
  { key: 'created_at', label: 'Created' },
  { key: 'owner', label: 'Owner' }
];

function changeSort(key) {
  let direction = 'asc';
  if (props.sortBy === key) {
    direction = props.sortDirection === 'asc' ? 'desc' : 'asc';
  }
  emit('update:sort', { sortBy: key, sortDirection: direction });
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background-color: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.status {
  font-weight: 600;
}

.status--processing {
  color: #f59e0b;
}

.status--ready {
  color: #10b981;
}

.status--error {
  color: #ef4444;
}

.actions a {
  color: #1f2937;
  font-weight: 600;
  text-decoration: none;
}
</style>
