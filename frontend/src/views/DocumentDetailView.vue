<template>
  <section v-if="document" class="document-detail">
    <header class="document-detail__header">
      <div>
        <h2>{{ document.title }}</h2>
        <p>
          Owner:
          {{ document.owner?.name || document.owner?.email || 'Unknown' }}
        </p>
      </div>
      <div class="document-detail__actions">
        <button class="button" type="button" @click="openEdit">Edit</button>
        <button class="button button--danger" type="button" @click="remove">
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
        <span class="label">Status</span>
        <span class="status" :class="`status--${document.status || 'ready'}`">
          {{ (document.status || 'ready').toUpperCase() }}
        </span>
      </div>
      <div>
        <span class="label">Vector Sync</span>
        <span>{{ document.vector_synced ? 'Synced' : 'Pending' }}</span>
      </div>
    </div>

    <div class="document-detail__tags">
      <span v-for="tag in document.tags || []" :key="tag" class="tag">{{
        tag
      }}</span>
    </div>

    <article class="document-detail__content">
      <h3>Content preview</h3>
      <pre>{{ document.content }}</pre>
    </article>

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
        <div class="form-field">
          <label for="edit-tags">Tags</label>
          <input
            id="edit-tags"
            v-model.trim="editForm.tags"
            type="text"
            placeholder="comma separated"
          />
        </div>
        <div
          class="form-field"
          :class="{ 'form-field--error': editErrors.content }"
        >
          <label for="edit-content">Content</label>
          <textarea
            id="edit-content"
            v-model="editForm.content"
            rows="8"
          ></textarea>
          <p v-if="editErrors.content" class="form-field__error">
            {{ editErrors.content }}
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
  </section>
  <section v-else class="document-detail__loading">Loading document…</section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import BaseModal from '@/components/BaseModal.vue';
import { useDocumentsStore } from '@/store/documents';

const route = useRoute();
const router = useRouter();
const documentsStore = useDocumentsStore();

const isEditOpen = ref(false);
const isSaving = ref(false);

const editForm = reactive({
  title: '',
  tags: '',
  content: ''
});

const editErrors = reactive({
  title: '',
  content: ''
});

const document = computed(() => documentsStore.activeDocument);

onMounted(() => {
  documentsStore.loadDocument(route.params.id);
});

watch(
  document,
  (value) => {
    if (!value) return;
    editForm.title = value.title;
    editForm.tags = (value.tags || []).join(', ');
    editForm.content = value.content;
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

function validate() {
  editErrors.title = editForm.title ? '' : 'Title is required.';
  editErrors.content = editForm.content ? '' : 'Content cannot be empty.';
  return !editErrors.title && !editErrors.content;
}

async function save() {
  if (!validate()) return;
  isSaving.value = true;
  try {
    await documentsStore.saveDocument(route.params.id, {
      title: editForm.title,
      tags: editForm.tags
        ? editForm.tags.split(',').map((tag) => tag.trim())
        : [],
      content: editForm.content
    });
    closeEdit();
    await documentsStore.loadDocument(route.params.id);
  } finally {
    isSaving.value = false;
  }
}

async function remove() {
  if (!confirm('Delete this document? This action cannot be undone.')) return;
  await documentsStore.removeDocument(route.params.id);
  router.push({ name: 'documents' });
}
</script>

<style scoped>
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
  margin-bottom: 24px;
}

.document-detail__meta .label {
  display: block;
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 4px;
}

.document-detail__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.document-detail__content {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.document-detail__content pre {
  white-space: pre-wrap;
  font-family: 'Menlo', 'Fira Code', monospace;
  color: #1f2937;
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
</style>
