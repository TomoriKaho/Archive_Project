<template>
  <section class="documents">
    <header class="documents__header">
      <div>
        <h2>Documents</h2>
        <p>
          Manage your knowledge assets and ensure they sync with the vector
          store.
        </p>
      </div>
      <button
        class="button button--primary"
        type="button"
        @click="openNewDocument"
      >
        New Document
      </button>
    </header>

    <div class="documents__controls">
      <div class="form-field">
        <label for="search">Search</label>
        <input
          id="search"
          v-model="search"
          type="search"
          placeholder="Search documents"
        />
      </div>
    </div>

    <DocumentTable
      :documents="documentsStore.items"
      :sort-by="documentsStore.filters.sort_by"
      :sort-direction="documentsStore.filters.sort_direction"
      @update:sort="onSort"
    />

    <BaseModal v-model="isModalOpen" title="Create Document">
      <BaseTabs v-model="activeTab" :tabs="tabs">
        <template #default="{ active }">
          <div v-if="active === 'text'" class="tab-pane">
            <div
              class="form-field"
              :class="{ 'form-field--error': textErrors.title }"
            >
              <label for="title">Title</label>
              <input
                id="title"
                v-model.trim="textForm.title"
                type="text"
                placeholder="Document title"
              />
              <p v-if="textErrors.title" class="form-field__error">
                {{ textErrors.title }}
              </p>
            </div>

            <div class="form-field">
              <label for="tags">Tags (comma separated)</label>
              <input
                id="tags"
                v-model.trim="textForm.tags"
                type="text"
                placeholder="research, ai"
              />
            </div>

            <div
              class="form-field"
              :class="{ 'form-field--error': textErrors.content }"
            >
              <label for="content">Content</label>
              <textarea
                id="content"
                v-model="textForm.content"
                rows="8"
                placeholder="Paste your content here"
              ></textarea>
              <p v-if="textErrors.content" class="form-field__error">
                {{ textErrors.content }}
              </p>
            </div>
          </div>
          <div v-else class="tab-pane">
            <div class="upload-zone" @dragover.prevent @drop.prevent="onDrop">
              <p>Drag & drop your CSV here or click to browse.</p>
              <input
                ref="fileInput"
                type="file"
                accept=".csv,text/csv"
                @change="onFileChange"
              />
              <button class="button" type="button" @click="fileInput?.click()">
                Select File
              </button>
              <p v-if="csvFile" class="upload-zone__file">
                Selected: {{ csvFile.name }}
              </p>
              <p v-if="csvError" class="form-field__error">{{ csvError }}</p>
            </div>
          </div>
        </template>
      </BaseTabs>

      <template #footer>
        <button class="button" type="button" @click="closeModal">Cancel</button>
        <button class="button button--primary" type="button" @click="submit">
          {{ isSubmitting ? 'Saving…' : 'Create' }}
        </button>
      </template>
    </BaseModal>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue';

import BaseModal from '@/components/BaseModal.vue';
import BaseTabs from '@/components/BaseTabs.vue';
import DocumentTable from '@/components/DocumentTable.vue';
import { useDocumentsStore } from '@/store/documents';

const documentsStore = useDocumentsStore();

const search = ref('');
const isModalOpen = ref(false);
const activeTab = ref('text');
const isSubmitting = ref(false);

const tabs = [
  { value: 'text', label: 'Plain Text' },
  { value: 'csv', label: 'CSV Upload' }
];

const textForm = reactive({
  title: '',
  tags: '',
  content: ''
});

const textErrors = reactive({
  title: '',
  content: ''
});

const csvFile = ref(null);
const csvError = ref('');
const fileInput = ref(null);

onMounted(() => {
  documentsStore.loadDocuments();
});

watch(
  () => search.value,
  (value) => {
    documentsStore.setSearch(value);
    documentsStore.loadDocuments({ search: value });
  }
);

function openNewDocument() {
  isModalOpen.value = true;
}

function closeModal() {
  isModalOpen.value = false;
  resetForms();
}

function resetForms() {
  textForm.title = '';
  textForm.tags = '';
  textForm.content = '';
  textErrors.title = '';
  textErrors.content = '';
  csvFile.value = null;
  csvError.value = '';
  activeTab.value = 'text';
}

function validateText() {
  textErrors.title = textForm.title ? '' : 'Title is required.';
  textErrors.content = textForm.content ? '' : 'Content cannot be empty.';
  return !textErrors.title && !textErrors.content;
}

function validateCsv(file) {
  csvError.value = '';
  if (!file) {
    csvError.value = 'Select a CSV file to upload.';
    return false;
  }
  const isCsv = file.type === 'text/csv' || file.name.endsWith('.csv');
  if (!isCsv) {
    csvError.value = 'Only CSV files are allowed.';
    return false;
  }
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    csvError.value = 'File exceeds 5MB limit.';
    return false;
  }
  return true;
}

function onFileChange(event) {
  const [file] = event.target.files;
  if (validateCsv(file)) {
    csvFile.value = file;
  } else {
    csvFile.value = null;
  }
}

function onDrop(event) {
  const [file] = event.dataTransfer.files;
  if (validateCsv(file)) {
    csvFile.value = file;
  } else {
    csvFile.value = null;
  }
}

async function submit() {
  if (activeTab.value === 'text') {
    if (!validateText()) return;
    isSubmitting.value = true;
    try {
      await documentsStore.createDocument({
        title: textForm.title,
        tags: textForm.tags
          ? textForm.tags.split(',').map((tag) => tag.trim())
          : [],
        content: textForm.content
      });
      closeModal();
    } finally {
      isSubmitting.value = false;
    }
  } else {
    if (!validateCsv(csvFile.value)) return;
    isSubmitting.value = true;
    try {
      const formData = new FormData();
      formData.append('file', csvFile.value);
      await documentsStore.uploadCsv(formData);
      closeModal();
    } finally {
      isSubmitting.value = false;
    }
  }
}

function onSort({ sortBy, sortDirection }) {
  documentsStore.setSorting({ sortBy, sortDirection });
  documentsStore.loadDocuments({
    sort_by: sortBy,
    sort_direction: sortDirection
  });
}
</script>

<style scoped>
.documents__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.documents__controls {
  margin-bottom: 24px;
  display: flex;
  gap: 16px;
}

.upload-zone {
  border: 2px dashed #cbd5f5;
  padding: 32px;
  text-align: center;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.upload-zone input[type='file'] {
  display: none;
}

.upload-zone__file {
  color: #1f2937;
}

.tab-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
</style>
