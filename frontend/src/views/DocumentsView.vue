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
      <div class="form-field">
        <label for="domain-filter">Domain</label>
        <select id="domain-filter" v-model="selectedDomainFilter">
          <option value="">All domains</option>
          <option
            v-for="domain in domainsStore.items"
            :key="domain.id"
            :value="String(domain.id)"
          >
            {{ domain.name }}
          </option>
        </select>
      </div>
    </div>

    <DocumentTable
      :documents="documentsStore.items"
      :domains="domainsStore.items"
      :sort-by="documentsStore.filters.sort_by"
      :sort-direction="documentsStore.filters.order"
      @update:sort="onSort"
    />

    <BaseModal v-model="isModalOpen" title="Create Document">
      <BaseTabs v-model="activeTab" :tabs="tabs">
        <template #default="{ active }">
          <div v-if="active === 'text'" class="tab-pane">
            <div
              class="form-field"
              :class="{ 'form-field--error': textErrors.domainId }"
            >
              <label for="text-domain">Domain</label>
              <select id="text-domain" v-model="textForm.domainId">
                <option value="">Select a domain</option>
                <option
                  v-for="domain in domainsStore.items"
                  :key="domain.id"
                  :value="String(domain.id)"
                >
                  {{ domain.name }}
                </option>
              </select>
              <p v-if="textErrors.domainId" class="form-field__error">
                {{ textErrors.domainId }}
              </p>
            </div>
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
            <div
              class="form-field"
              :class="{ 'form-field--error': csvErrors.domainId }"
            >
              <label for="csv-domain">Domain</label>
              <select id="csv-domain" v-model="csvForm.domainId">
                <option value="">Select a domain</option>
                <option
                  v-for="domain in domainsStore.items"
                  :key="domain.id"
                  :value="String(domain.id)"
                >
                  {{ domain.name }}
                </option>
              </select>
              <p v-if="csvErrors.domainId" class="form-field__error">
                {{ csvErrors.domainId }}
              </p>
            </div>
            <div
              class="form-field"
              :class="{ 'form-field--error': csvErrors.title }"
            >
              <label for="csv-title">Title</label>
              <input
                id="csv-title"
                v-model.trim="csvForm.title"
                type="text"
                placeholder="Document title"
              />
              <p v-if="csvErrors.title" class="form-field__error">
                {{ csvErrors.title }}
              </p>
            </div>
            <div class="form-field">
              <label for="csv-tags">Tags (comma separated)</label>
              <input
                id="csv-tags"
                v-model.trim="csvForm.tags"
                type="text"
                placeholder="research, ai"
              />
            </div>
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
              <p v-if="csvErrors.file" class="form-field__error">
                {{ csvErrors.file }}
              </p>
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
import { useDomainsStore } from '@/store/domains';

const documentsStore = useDocumentsStore();
const domainsStore = useDomainsStore();

const search = ref('');
const selectedDomainFilter = ref('');
const isModalOpen = ref(false);
const activeTab = ref('text');
const isSubmitting = ref(false);

const tabs = [
  { value: 'text', label: 'Plain Text' },
  { value: 'csv', label: 'CSV Upload' }
];

const textForm = reactive({
  domainId: '',
  title: '',
  tags: '',
  content: ''
});

const textErrors = reactive({
  domainId: '',
  title: '',
  content: ''
});

const csvForm = reactive({
  domainId: '',
  title: '',
  tags: ''
});

const csvErrors = reactive({
  domainId: '',
  title: '',
  file: ''
});

const csvFile = ref(null);
const fileInput = ref(null);

onMounted(() => {
  documentsStore.loadDocuments();
  domainsStore.loadDomains();
});

watch(
  () => search.value,
  () => {
    documentsStore.setSearch(search.value);
    documentsStore.loadDocuments();
  }
);

watch(
  () => selectedDomainFilter.value,
  (value) => {
    const domainId = value ? Number(value) : null;
    documentsStore.setDomainFilter(domainId);
    const query = domainId ? { domain_id: domainId } : {};
    documentsStore.loadDocuments(query);
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
  textForm.domainId = '';
  textForm.title = '';
  textForm.tags = '';
  textForm.content = '';
  textErrors.domainId = '';
  textErrors.title = '';
  textErrors.content = '';
  csvForm.domainId = '';
  csvForm.title = '';
  csvForm.tags = '';
  csvErrors.domainId = '';
  csvErrors.title = '';
  csvErrors.file = '';
  csvFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  activeTab.value = 'text';
}

function validateText() {
  textErrors.domainId = textForm.domainId ? '' : 'Select a domain.';
  textErrors.title = textForm.title ? '' : 'Title is required.';
  textErrors.content = textForm.content ? '' : 'Content cannot be empty.';
  return !textErrors.domainId && !textErrors.title && !textErrors.content;
}

function validateCsvFile(file) {
  csvErrors.file = '';
  if (!file) {
    csvErrors.file = 'Select a CSV file to upload.';
    return false;
  }
  const isCsv = file.type === 'text/csv' || file.name.endsWith('.csv');
  if (!isCsv) {
    csvErrors.file = 'Only CSV files are allowed.';
    return false;
  }
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    csvErrors.file = 'File exceeds 5MB limit.';
    return false;
  }
  return true;
}

function onFileChange(event) {
  const [file] = event.target.files;
  if (validateCsvFile(file)) {
    csvFile.value = file;
  } else {
    csvFile.value = null;
  }
}

function onDrop(event) {
  const [file] = event.dataTransfer.files;
  if (validateCsvFile(file)) {
    csvFile.value = file;
  } else {
    csvFile.value = null;
  }
}

function validateCsvForm() {
  csvErrors.domainId = csvForm.domainId ? '' : 'Select a domain.';
  csvErrors.title = csvForm.title ? '' : 'Title is required.';
  const fileValid = validateCsvFile(csvFile.value);
  return !csvErrors.domainId && !csvErrors.title && fileValid;
}

function parseTags(raw) {
  if (!raw) return [];
  return raw
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);
}

async function submit() {
  if (activeTab.value === 'text') {
    if (!validateText()) return;
    isSubmitting.value = true;
    try {
      await documentsStore.createDocument({
        domainId: Number(textForm.domainId),
        title: textForm.title,
        tags: parseTags(textForm.tags),
        content: textForm.content
      });
      closeModal();
    } finally {
      isSubmitting.value = false;
    }
  } else {
    if (!validateCsvForm()) return;
    isSubmitting.value = true;
    try {
      await documentsStore.uploadCsv({
        domainId: Number(csvForm.domainId),
        title: csvForm.title,
        tags: parseTags(csvForm.tags),
        file: csvFile.value
      });
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
    order: sortDirection
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
