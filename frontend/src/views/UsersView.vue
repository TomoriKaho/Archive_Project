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
          <td>
            <input
              v-model.trim="draft.full_name"
              type="text"
              placeholder="Name (optional)"
            />
          </td>
          <td>{{ user.email }}</td>
          <td>
            <label class="toggle">
              <input type="checkbox" v-model="draft.is_admin" />
              <span>{{ draft.is_admin ? 'Admin' : 'User' }}</span>
            </label>
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
            <button class="button" type="button" @click="saveUser(user.id)">
              {{ savingUserId === user.id ? 'Saving…' : 'Save' }}
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
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';

import { useUsersStore } from '@/store/users';
import { useAuthStore } from '@/store/auth';

const usersStore = useUsersStore();
const authStore = useAuthStore();

const userDraft = reactive({});
const savingUserId = ref(null);
const deletingUserId = ref(null);

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

const usersWithDrafts = computed(() =>
  usersStore.items.map((user) => ({
    user,
    draft: ensureDraft(user)
  }))
);

const currentUserId = computed(() => authStore.user?.id ?? null);

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

async function saveUser(userId) {
  const id = String(userId);
  savingUserId.value = userId;
  try {
    await usersStore.saveUser(userId, userDraft[id]);
  } finally {
    savingUserId.value = null;
  }
}

async function deleteUser(userId) {
  if (userId === currentUserId.value) return;
  deletingUserId.value = userId;
  try {
    await usersStore.removeUser(userId);
  } finally {
    deletingUserId.value = null;
  }
}

function deleteButtonLabel(user) {
  if (deletingUserId.value === user.id) {
    return 'Deleting…';
  }
  if (user.id === currentUserId.value) {
    return 'Cannot delete';
  }
  return 'Delete';
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

.users__table input[type='text'] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
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
  margin-left: 8px;
}

.button--danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
