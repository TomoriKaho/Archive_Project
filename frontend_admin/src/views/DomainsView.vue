<template>
  <section class="domains">
    <header class="domains__header">
      <div>
        <h2>{{ t('domains.title') }}</h2>
        <p>{{ t('domains.subtitle') }}</p>
      </div>
      <button class="button button--primary" type="button" @click="openCreate">
        {{ t('domains.actions.new') }}
      </button>
    </header>

    <table class="domains__table">
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
        <tr v-if="domainsStore.items.length === 0">
          <td colspan="6" class="empty">{{ t('domains.empty') }}</td>
        </tr>
        <tr v-for="domain in domainsStore.items" :key="domain.id">
          <td>{{ domain.name }}</td>
          <td>{{ domain.description || '—' }}</td>
          <td>{{ domain.language || '—' }}</td>
          <td>{{ formatDate(domain.created_at) }}</td>
          <td>{{ formatDate(domain.updated_at) }}</td>
          <td class="actions">
            <button type="button" @click="openEdit(domain)">
              {{ t('common.edit') }}
            </button>
            <button
              type="button"
              class="button--link-danger"
              @click="promptRemove(domain)"
            >
              {{ t('common.delete') }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <BaseModal v-model="isModalOpen" :title="modalTitle">
      <div class="form-field" :class="{ 'form-field--error': errors.name }">
        <label for="domain-name">{{ t('domains.form.nameLabel') }}</label>
        <input id="domain-name" v-model.trim="form.name" type="text" />
        <p v-if="errors.name" class="form-field__error">{{ errors.name }}</p>
      </div>
      <div class="form-field">
        <label for="domain-description">{{ t('domains.form.descriptionLabel') }}</label>
        <textarea
          id="domain-description"
          v-model="form.description"
          rows="3"
          :placeholder="t('domains.form.descriptionPlaceholder')"
        ></textarea>
      </div>
      <div class="form-field">
        <label for="domain-language">{{ t('domains.form.languageLabel') }}</label>
        <select id="domain-language" v-model="form.language">
          <option value="">{{ t('domains.form.languagePlaceholder') }}</option>
          <option v-for="option in languageOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>
      <p class="form-hint">{{ t('domains.form.hint') }}</p>
      <template #footer>
        <button class="button" type="button" @click="closeModal">
          {{ t('common.cancel') }}
        </button>
        <button class="button button--primary" type="button" @click="submit">
          {{ isSaving ? t('common.saving') : t('common.save') }}
        </button>
      </template>
    </BaseModal>
    <BaseModal v-model="isDeleteModalOpen" :title="t('domains.delete.title')">
      <p>{{ t('domains.delete.message') }}</p>
      <template #footer>
        <button class="button" type="button" @click="closeDeleteModal">
          {{ t('common.cancel') }}
        </button>
        <button
          class="button button--danger"
          type="button"
          :disabled="isDeleting"
          @click="confirmRemove"
        >
          {{ isDeleting ? t('common.deleting') : t('domains.delete.confirm') }}
        </button>
      </template>
    </BaseModal>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import BaseModal from '@/components/BaseModal.vue';
import { useDomainsStore } from '@/store/domains';

const domainsStore = useDomainsStore();
const { t, locale } = useI18n();

const languageOptions = [
  { value: 'en', label: 'English / 英语 (en)' },
  { value: 'zh', label: '简体中文 / Chinese (zh)' },
  { value: 'zh_tw', label: '繁体中文 / Traditional Chinese (zh_tw)' },
  { value: 'ru', label: 'Russian / 俄语 (ru)' },
  { value: 'ja', label: 'Japanese / 日语 (ja)' },
  { value: 'ko', label: 'Korean / 韩语 (ko)' },
  { value: 'es', label: 'Spanish / 西班牙语 (es)' },
  { value: 'fr', label: 'French / 法语 (fr)' },
  { value: 'pt', label: 'Portuguese / 葡萄牙语 (pt)' },
  { value: 'de', label: 'German / 德语 (de)' },
  { value: 'it', label: 'Italian / 意大利语 (it)' },
  { value: 'th', label: 'Thai / 泰语 (th)' },
  { value: 'vi', label: 'Vietnamese / 越南语 (vi)' },
  { value: 'id', label: 'Indonesian / 印度尼西亚语 (id)' },
  { value: 'ms', label: 'Malay / 马来语 (ms)' },
  { value: 'ar', label: 'Arabic / 阿拉伯语 (ar)' },
  { value: 'hi', label: 'Hindi / 印地语 (hi)' },
  { value: 'he', label: 'Hebrew / 希伯来语 (he)' },
  { value: 'ur', label: 'Urdu / 乌尔都语 (ur)' },
  { value: 'bn', label: 'Bengali / 孟加拉语 (bn)' },
  { value: 'pl', label: 'Polish / 波兰语 (pl)' },
  { value: 'nl', label: 'Dutch / 荷兰语 (nl)' },
  { value: 'tr', label: 'Turkish / 土耳其语 (tr)' },
  { value: 'km', label: 'Khmer / 高棉语 (km)' },
  { value: 'cs', label: 'Czech / 捷克语 (cs)' },
  { value: 'sv', label: 'Swedish / 瑞典语 (sv)' },
  { value: 'hu', label: 'Hungarian / 匈牙利语 (hu)' },
  { value: 'da', label: 'Danish / 丹麦语 (da)' },
  { value: 'fi', label: 'Finnish / 芬兰语 (fi)' },
  { value: 'tl', label: 'Tagalog / 他加禄语 (tl)' },
  { value: 'fa', label: 'Persian / 波斯语 (fa)' }
];

const columns = computed(() => [
  { key: 'name', label: t('domains.table.name'), sortable: true },
  { key: 'description', label: t('domains.table.description'), sortable: true },
  { key: 'language', label: t('domains.table.language'), sortable: true },
  { key: 'created_at', label: t('domains.table.created'), sortable: true },
  { key: 'updated_at', label: t('domains.table.updated'), sortable: true }
]);

const sortBy = computed(() => domainsStore.filters.sort_by);
const sortDirection = computed(() => domainsStore.filters.order);

const isModalOpen = ref(false);
const isDeleteModalOpen = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const editingDomainId = ref(null);
const deletingDomainId = ref(null);

const form = reactive({
  name: '',
  description: '',
  language: ''
});

const errors = reactive({
  name: ''
});

const modalTitle = computed(() =>
  editingDomainId.value ? t('domains.modal.editTitle') : t('domains.modal.newTitle')
);

onMounted(() => {
  domainsStore.loadDomains();
});

function changeSort(key) {
  let direction = 'asc';
  if (sortBy.value === key) {
    direction = sortDirection.value === 'asc' ? 'desc' : 'asc';
  }
  domainsStore.setSorting({ sortBy: key, sortDirection: direction });
  domainsStore.loadDomains({ sort_by: key, order: direction });
}

function openCreate() {
  editingDomainId.value = null;
  form.name = '';
  form.description = '';
  form.language = '';
  errors.name = '';
  isModalOpen.value = true;
}

function openEdit(domain) {
  editingDomainId.value = domain.id;
  form.name = domain.name;
  form.description = domain.description;
  form.language = domain.language || '';
  errors.name = '';
  isModalOpen.value = true;
}

function closeModal() {
  isModalOpen.value = false;
}

function validate() {
  errors.name = form.name ? '' : t('domains.form.validation.nameRequired');
  return !errors.name;
}

async function submit() {
  if (!validate()) return;
  isSaving.value = true;
  const payload = {
    name: form.name,
    description: form.description,
    language: form.language || null
  };
  try {
    const success = editingDomainId.value
      ? await domainsStore.update(editingDomainId.value, payload)
      : await domainsStore.create(payload);
    if (success) {
      closeModal();
    }
  } catch (error) {
    // The domain store already displays error toasts. Keep the modal open so the
    // user can adjust the form.
  } finally {
    isSaving.value = false;
  }
}

function promptRemove(domain) {
  deletingDomainId.value = domain.id;
  isDeleteModalOpen.value = true;
}

function closeDeleteModal() {
  isDeleteModalOpen.value = false;
  deletingDomainId.value = null;
}

async function confirmRemove() {
  if (!deletingDomainId.value || isDeleting.value) return;
  isDeleting.value = true;
  try {
    await domainsStore.remove(deletingDomainId.value);
    closeDeleteModal();
  } finally {
    isDeleting.value = false;
  }
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString(locale.value);
  } catch (error) {
    return new Date(value).toLocaleString();
  }
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
