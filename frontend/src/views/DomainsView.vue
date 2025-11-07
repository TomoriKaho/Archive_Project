<template>
  <section class="domains">
    <header class="domains__header">
      <div>
        <h2>Domains</h2>
        <p>Manage domains available for document ingestion.</p>
      </div>
      <button class="button button--primary" type="button" @click="openCreate">
        New Domain
      </button>
    </header>

    <table class="domains__table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Description</th>
          <th>Created</th>
          <th>Updated</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="domainsStore.items.length === 0">
          <td colspan="4" class="empty">No domains found.</td>
        </tr>
        <tr v-for="domain in domainsStore.items" :key="domain.id">
          <td>{{ domain.name }}</td>
          <td>{{ domain.description || '—' }}</td>
          <td>{{ formatDate(domain.created_at) }}</td>
          <td>{{ formatDate(domain.updated_at) }}</td>
          <td class="actions">
            <button type="button" @click="openEdit(domain)">Edit</button>
            <button
              type="button"
              class="button--link-danger"
              @click="remove(domain)"
            >
              Delete
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <BaseModal v-model="isModalOpen" :title="modalTitle">
      <div class="form-field" :class="{ 'form-field--error': errors.name }">
        <label for="domain-name">Name</label>
        <input id="domain-name" v-model.trim="form.name" type="text" />
        <p v-if="errors.name" class="form-field__error">{{ errors.name }}</p>
      </div>
      <div class="form-field">
        <label for="domain-description">Description</label>
        <textarea
          id="domain-description"
          v-model="form.description"
          rows="3"
        ></textarea>
      </div>
      <p class="form-hint">Domains are always active once created.</p>
      <template #footer>
        <button class="button" type="button" @click="closeModal">Cancel</button>
        <button class="button button--primary" type="button" @click="submit">
          {{ isSaving ? 'Saving…' : 'Save' }}
        </button>
      </template>
    </BaseModal>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';

import BaseModal from '@/components/BaseModal.vue';
import { useDomainsStore } from '@/store/domains';

const domainsStore = useDomainsStore();

const isModalOpen = ref(false);
const isSaving = ref(false);
const editingDomainId = ref(null);

const form = reactive({
  name: '',
  description: ''
});

const errors = reactive({
  name: ''
});

const modalTitle = computed(() =>
  editingDomainId.value ? 'Edit Domain' : 'New Domain'
);

onMounted(() => {
  domainsStore.loadDomains();
});

function openCreate() {
  editingDomainId.value = null;
  form.name = '';
  form.description = '';
  errors.name = '';
  isModalOpen.value = true;
}

function openEdit(domain) {
  editingDomainId.value = domain.id;
  form.name = domain.name;
  form.description = domain.description;
  errors.name = '';
  isModalOpen.value = true;
}

function closeModal() {
  isModalOpen.value = false;
}

function validate() {
  errors.name = form.name ? '' : 'Name is required.';
  return !errors.name;
}

async function submit() {
  if (!validate()) return;
  isSaving.value = true;
  const payload = {
    name: form.name,
    description: form.description
  };
  try {
    if (editingDomainId.value) {
      await domainsStore.update(editingDomainId.value, payload);
    } else {
      await domainsStore.create(payload);
    }
    closeModal();
  } finally {
    isSaving.value = false;
  }
}

async function remove(domain) {
  if (!confirm(`Delete ${domain.name}?`)) return;
  await domainsStore.remove(domain.id);
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}
</script>

<style scoped>
.domains__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.domains__table {
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
  border-bottom: 1px solid #f3f4f6;
  text-align: left;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 32px 16px;
}

.actions {
  display: flex;
  gap: 12px;
}

.button--link-danger {
  color: #ef4444;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
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

.form-hint {
  margin: 12px 0 0;
  color: #6b7280;
  font-size: 14px;
}
</style>
