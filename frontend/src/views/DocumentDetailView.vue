<template>
  <section v-if="document" class="document-detail">
    <header class="document-detail__header">
      <div>
        <h2>{{ document.title }}</h2>
        <p>Domain: {{ domainName }}</p>
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
        <span class="label">UUID</span>
        <span class="mono">{{ document.uuid }}</span>
      </div>
      <div>
        <span class="label">Domain ID</span>
        <span>{{ document.domain_id }}</span>
      </div>
    </div>

    <div v-if="tags.length" class="document-detail__tags">
      <span v-for="tag in tags" :key="tag" class="tag">{{ tag }}</span>
    </div>
    <p v-else class="document-detail__empty">
      No tags attached to this document.
    </p>

    <article class="document-detail__content">
      <h3>Metadata</h3>
      <p class="document-detail__hint">
        Documents are chunked on ingestion, so only metadata is stored alongside
        the vectorised content.
      </p>
      <pre>{{ formattedMetadata }}</pre>
    </article>

    <article class="document-detail__content document-detail__chunks">
      <header class="document-detail__chunks-header">
        <h3>Chunks</h3>
        <span class="document-detail__hint">
          {{ chunks.length }}
          {{ chunks.length === 1 ? 'chunk' : 'chunks' }}
          stored for this document.
        </span>
      </header>
      <p v-if="!chunks.length" class="document-detail__empty">
        No chunks have been generated for this document yet.
      </p>
      <ul v-else class="chunk-list">
        <li v-for="chunk in chunks" :key="chunk.id" class="chunk-list__item">
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
import { useDomainsStore } from '@/store/domains';

const route = useRoute();
const router = useRouter();
const documentsStore = useDocumentsStore();
const domainsStore = useDomainsStore();

const isEditOpen = ref(false);
const isSaving = ref(false);

const editForm = reactive({
  title: '',
  tags: ''
});

const editErrors = reactive({
  title: ''
});

const document = computed(() => documentsStore.activeDocument);
const chunks = computed(() => documentsStore.activeChunks || []);
const tags = computed(() => {
  if (!document.value?.doc_metadata?.tags) return [];
  return document.value.doc_metadata.tags.filter((tag) => tag);
});
const formattedMetadata = computed(() =>
  document.value
    ? JSON.stringify(document.value.doc_metadata ?? {}, null, 2)
    : '{}'
);
const domainName = computed(() => {
  const domain = domainsStore.items.find(
    (item) => item.id === document.value?.domain_id
  );
  if (!document.value) return '—';
  return domain?.name || `Domain #${document.value.domain_id}`;
});

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
    editForm.tags = tags.value.join(', ');
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

function parseTags(raw) {
  if (!raw) return [];
  return raw
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function formatChunkLength(chunk) {
  if (!chunk || typeof chunk.content !== 'string') return 0;
  return chunk.content.length;
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
      tags: parseTags(editForm.tags),
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
  if (!confirm('Delete this document? This action cannot be undone.')) return;
  await documentsStore.removeDocument({
    documentId: document.value.id,
    domainId: document.value.domain_id
  });
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

.document-detail__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.tag {
  background-color: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
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
