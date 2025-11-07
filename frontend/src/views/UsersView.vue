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
          <th>New password</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="usersWithDrafts.length === 0">
          <td colspan="6" class="empty">No users found.</td>
        </tr>
        <tr v-for="{ user, draft } in usersWithDrafts" :key="user.id">
          <td>{{ user.full_name || '—' }}</td>
          <td>{{ user.email }}</td>
          <td>
            <span
              :class="[
                'badge',
                draft.is_admin ? 'badge--admin' : 'badge--user'
              ]"
            >
              {{ draft.is_admin ? 'Admin' : 'User' }}
            </span>
          </td>
          <td>
            <input
              v-model.trim="draft.password"
              type="password"
              placeholder="Set new password"
            />
          </td>
          <td>{{ formatDate(user.created_at) }}</td>
          <td>
            <button class="button" type="button" @click="openEditUser(user.id)">
              Edit
            </button>
            <button
              class="button button--danger"
              type="button"
              :disabled="
                deletingUserId === user.id || user.id === currentUserId
              "
              @click="deleteUser(user.id)"
            >
              {{ deleteButtonLabel(user) }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <BaseModal
      v-if="editingUser"
      v-model="isEditModalOpen"
      :title="`Edit ${editingUser.full_name || editingUser.email}`"
    >
      <div class="form-field">
        <label for="user-name">Name</label>
        <input
          id="user-name"
          v-model.trim="editingDraft.full_name"
          type="text"
          placeholder="Name (optional)"
        />
      </div>

      <div class="form-field">
        <label class="toggle">
          <input type="checkbox" v-model="editingDraft.is_admin" />
          <span>
            {{ editingDraft.is_admin ? 'Administrator' : 'Standard user' }}
          </span>
        </label>
      </div>

      <div class="form-field">
        <label for="user-password">New password</label>
        <input
          id="user-password"
          v-model.trim="editingDraft.password"
          type="password"
          placeholder="Leave blank to keep current password"
        />
        <p class="form-field__hint">
          Leave blank to keep the existing password.
        </p>
      </div>

      <div
        v-if="isDeleteConfirmationVisible"
        class="delete-confirmation"
        role="alert"
      >
        <p>
          Deleting this user will remove their access immediately. This action
          cannot be undone. Do you still want to proceed?
        </p>
      </div>

      <template #footer>
        <button
          class="button"
          type="button"
          @click="
            isDeleteConfirmationVisible
              ? cancelDeleteRequest()
              : closeEditUser()
          "
        >
          {{ isDeleteConfirmationVisible ? 'Back' : 'Cancel' }}
        </button>

        <template v-if="isDeleteConfirmationVisible">
          <button
            class="button button--danger"
            type="button"
            :disabled="deletingUserId === editingUser.id"
            @click="confirmDeleteUser()"
          >
            {{
              deletingUserId === editingUser.id ? 'Deleting…' : 'Delete user'
            }}
          </button>
        </template>
        <template v-else>
          <button
            class="button button--primary"
            type="button"
            :disabled="savingUserId === editingUser.id"
            @click="saveEditingUser"
          >
            {{ savingUserId === editingUser.id ? 'Saving…' : 'Save changes' }}
          </button>
          <button
            v-if="editingUser.id !== currentUserId"
            class="button button--danger"
            type="button"
            :disabled="deletingUserId === editingUser.id"
            @click="requestDeleteUser()"
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

import { useUsersStore } from '@/store/users';
import { useAuthStore } from '@/store/auth';
import BaseModal from '@/components/BaseModal.vue';

const usersStore = useUsersStore();
const authStore = useAuthStore();

const userDraft = reactive({});
const savingUserId = ref(null);
const deletingUserId = ref(null);
const isEditModalOpen = ref(false);
const editingUserId = ref(null);
const isDeleteConfirmationVisible = ref(false);

onMounted(async () => {
  if (!authStore.initialized) {
    authStore.initialize();
  }
  await usersStore.loadUsers();
  initializeDraft();
});

watch(
  () => usersStore.items,
  () => {
    initializeDraft();
  }
);

watch(isEditModalOpen, (value) => {
  if (!value) {
    const id = editingUserId.value;
    if (id !== null) {
      const user = usersStore.items.find((item) => item.id === id);
      if (user) {
        const draft = ensureDraft(user);
        draft.full_name = user.full_name ?? '';
        draft.is_admin = !!user.is_admin;
        draft.password = '';
      }
    }
    editingUserId.value = null;
    isDeleteConfirmationVisible.value = false;
  }
});

const usersWithDrafts = computed(() =>
  usersStore.items.map((user) => ({
    user,
    draft: ensureDraft(user)
  }))
);

const currentUserId = computed(() => authStore.user?.id ?? null);

const editingUser = computed(
  () => usersStore.items.find((user) => user.id === editingUserId.value) || null
);

const editingDraft = computed(() => {
  if (!editingUser.value) {
    return null;
  }
  return ensureDraft(editingUser.value);
});

function initializeDraft() {
  const validIds = new Set(usersStore.items.map((user) => String(user.id)));

  Object.keys(userDraft).forEach((id) => {
    if (!validIds.has(id)) {
      delete userDraft[id];
    }
  });

  usersStore.items.forEach((user) => {
    const draft = ensureDraft(user);
    draft.full_name = user.full_name ?? '';
    draft.is_admin = !!user.is_admin;
    draft.password = '';
  });
}

function ensureDraft(user) {
  const id = String(user.id);
  if (!userDraft[id]) {
    userDraft[id] = {
      full_name: user.full_name ?? '',
      is_admin: !!user.is_admin,
      password: ''
    };
  }
  return userDraft[id];
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function openEditUser(userId) {
  editingUserId.value = userId;
  isDeleteConfirmationVisible.value = false;
  isEditModalOpen.value = true;
}

function closeEditUser() {
  isEditModalOpen.value = false;
}

async function saveEditingUser() {
  if (!editingUser.value) return;
  const id = editingUser.value.id;
  savingUserId.value = id;
  try {
    await usersStore.saveUser(id, userDraft[String(id)]);
    closeEditUser();
  } finally {
    savingUserId.value = null;
  }
}

function requestDeleteUser() {
  if (!editingUser.value || editingUser.value.id === currentUserId.value) {
    return;
  }
  isDeleteConfirmationVisible.value = true;
}

function cancelDeleteRequest() {
  isDeleteConfirmationVisible.value = false;
}

async function confirmDeleteUser() {
  if (!editingUser.value) return;
  const id = editingUser.value.id;
  if (id === currentUserId.value) return;
  deletingUserId.value = id;
  try {
    await usersStore.removeUser(id);
    closeEditUser();
  } finally {
    deletingUserId.value = null;
    isDeleteConfirmationVisible.value = false;
  }
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
