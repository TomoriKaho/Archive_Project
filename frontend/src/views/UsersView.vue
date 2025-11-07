<template>
  <section class="users">
    <header class="users__header">
      <div>
        <h2>Users</h2>
        <p>Manage roles, passwords, and access.</p>
      </div>
    </header>

    <table class="users__table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Admin</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="usersStore.items.length === 0">
          <td colspan="5" class="empty">No users found.</td>
        </tr>
        <tr v-for="user in usersStore.items" :key="user.id">
          <td>{{ user.full_name || '—' }}</td>
          <td>{{ user.email }}</td>
          <td>
            <span
              :class="['badge', user.is_admin ? 'badge--admin' : 'badge--user']"
            >
              {{ user.is_admin ? 'Admin' : 'User' }}
            </span>
          </td>
          <td>{{ formatDate(user.created_at) }}</td>
          <td>
            <button class="button" type="button" @click="openEditUser(user.id)">
              Edit
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <BaseModal
      v-if="editingUser"
      v-model="isModalOpen"
      :title="`Edit ${editingUser.full_name || editingUser.email}`"
    >
      <div class="form-field">
        <label for="user-name">Name</label>
        <input
          id="user-name"
          v-model.trim="editingForm.full_name"
          type="text"
          placeholder="Name (optional)"
        />
      </div>

      <div class="form-field">
        <label class="toggle">
          <input type="checkbox" v-model="editingForm.is_admin" />
          <span>
            {{ editingForm.is_admin ? 'Administrator' : 'Standard user' }}
          </span>
        </label>
      </div>

      <div class="form-field">
        <label for="user-password">New password</label>
        <input
          id="user-password"
          v-model.trim="editingForm.password"
          type="password"
          placeholder="Leave blank to keep current password"
        />
        <p class="form-field__hint">
          Leave blank to keep the existing password.
        </p>
      </div>

      <div v-if="showDeleteConfirm" class="delete-confirmation" role="alert">
        <p>
          Deleting this user will remove their access immediately. This action
          cannot be undone. Do you still want to proceed?
        </p>
      </div>

      <template #footer>
        <button class="button" type="button" @click="onBackOrCancel">
          {{ showDeleteConfirm ? 'Back' : 'Cancel' }}
        </button>

        <template v-if="showDeleteConfirm">
          <button
            class="button button--danger"
            type="button"
            :disabled="deleting"
            @click="confirmDelete"
          >
            {{ deleting ? 'Deleting…' : 'Delete user' }}
          </button>
        </template>
        <template v-else>
          <button
            class="button button--primary"
            type="button"
            :disabled="saving"
            @click="saveUser"
          >
            {{ saving ? 'Saving…' : 'Save changes' }}
          </button>
          <button
            v-if="!isEditingSelf"
            class="button button--danger"
            type="button"
            :disabled="deleting"
            @click="requestDelete"
          >
            Delete user
          </button>
        </template>
      </template>
    </BaseModal>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';

import BaseModal from '@/components/BaseModal.vue';
import { useAuthStore } from '@/store/auth';
import { useUsersStore } from '@/store/users';

const usersStore = useUsersStore();
const authStore = useAuthStore();

const isModalOpen = ref(false);
const editingUserId = ref(null);
const showDeleteConfirm = ref(false);
const saving = ref(false);
const deleting = ref(false);

const editingForm = reactive({
  full_name: '',
  is_admin: false,
  password: ''
});

onMounted(async () => {
  if (!authStore.initialized) {
    authStore.initialize();
  }
  await usersStore.loadUsers();
});

watch(
  () => usersStore.items,
  () => {
    if (!editingUserId.value) return;
    const latest = usersStore.items.find(
      (item) => item.id === editingUserId.value
    );
    if (!latest) {
      closeModal();
      return;
    }
    populateForm(latest);
  }
);

const currentUserId = computed(() => authStore.user?.id ?? null);

const editingUser = computed(() => {
  return (
    usersStore.items.find((user) => user.id === editingUserId.value) || null
  );
});

const isEditingSelf = computed(() => {
  return editingUser.value?.id === currentUserId.value;
});

function populateForm(user) {
  editingForm.full_name = user.full_name ?? '';
  editingForm.is_admin = !!user.is_admin;
  editingForm.password = '';
}

function openEditUser(userId) {
  const user = usersStore.items.find((item) => item.id === userId);
  if (!user) return;
  editingUserId.value = userId;
  populateForm(user);
  showDeleteConfirm.value = false;
  isModalOpen.value = true;
}

function onBackOrCancel() {
  if (showDeleteConfirm.value) {
    showDeleteConfirm.value = false;
  } else {
    closeModal();
  }
}

function closeModal() {
  isModalOpen.value = false;
  editingUserId.value = null;
  showDeleteConfirm.value = false;
  editingForm.full_name = '';
  editingForm.is_admin = false;
  editingForm.password = '';
}

async function saveUser() {
  if (!editingUser.value) return;
  saving.value = true;
  try {
    await usersStore.saveUser(editingUser.value.id, { ...editingForm });
    closeModal();
  } finally {
    saving.value = false;
  }
}

function requestDelete() {
  if (isEditingSelf.value) return;
  showDeleteConfirm.value = true;
}

async function confirmDelete() {
  if (!editingUser.value || isEditingSelf.value) return;
  deleting.value = true;
  try {
    await usersStore.removeUser(editingUser.value.id);
    closeModal();
  } finally {
    deleting.value = false;
    showDeleteConfirm.value = false;
  }
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}
</script>

<style scoped>
.users__table {
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

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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
  background: #fee2e2;
  color: #b91c1c;
}

.button--danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
}

.badge--admin {
  background: #1f2937;
  color: #ffffff;
}

.badge--user {
  background: #e5e7eb;
  color: #1f2937;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.form-field label {
  font-weight: 600;
}

.form-field input[type='text'],
.form-field input[type='password'] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
}

.form-field__hint {
  color: #6b7280;
  font-size: 13px;
}

.delete-confirmation {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 16px;
  color: #991b1b;
  margin-top: 8px;
}
</style>
