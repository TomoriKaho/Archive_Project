<template>
  <section class="users">
    <header class="users__header">
      <div>
        <h2>Users</h2>
        <p>Manage roles and send invitations.</p>
      </div>
    </header>

    <section class="users__invite">
      <h3>Invite a user</h3>
      <div class="invite-form">
        <div
          class="form-field"
          :class="{ 'form-field--error': inviteErrors.email }"
        >
          <label for="invite-email">Email</label>
          <input
            id="invite-email"
            v-model.trim="inviteForm.email"
            type="email"
            placeholder="person@example.com"
          />
          <p v-if="inviteErrors.email" class="form-field__error">
            {{ inviteErrors.email }}
          </p>
        </div>
        <div class="form-field">
          <label for="invite-role">Role</label>
          <select id="invite-role" v-model="inviteForm.role">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <button
          class="button button--primary"
          type="button"
          @click="inviteUser"
        >
          {{ isInviting ? 'Sending…' : 'Send invite' }}
        </button>
      </div>
    </section>

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
        <tr v-if="usersWithDrafts.length === 0">
          <td colspan="5" class="empty">No users found.</td>
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
          <td>{{ formatDate(user.created_at) }}</td>
          <td>
            <button class="button" type="button" @click="saveUser(user.id)">
              {{ savingUserId === user.id ? 'Saving…' : 'Save' }}
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

const usersStore = useUsersStore();

const userDraft = reactive({});
const savingUserId = ref(null);

const inviteForm = reactive({
  email: '',
  role: 'user'
});
const inviteErrors = reactive({
  email: ''
});
const isInviting = ref(false);

onMounted(async () => {
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
  });
}

function ensureDraft(user) {
  const id = String(user.id);
  if (!userDraft[id]) {
    userDraft[id] = {
      full_name: user.full_name ?? '',
      is_admin: !!user.is_admin
    };
  }
  return userDraft[id];
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function validateInvite() {
  inviteErrors.email = inviteForm.email ? '' : 'Email is required.';
  return !inviteErrors.email;
}

async function inviteUser() {
  if (!validateInvite()) return;
  isInviting.value = true;
  try {
    await usersStore.invite({ ...inviteForm });
    inviteForm.email = '';
    inviteForm.role = 'user';
  } finally {
    isInviting.value = false;
  }
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
</script>

<style scoped>
.users__invite {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
  margin-bottom: 24px;
}

.invite-form {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.invite-form .form-field {
  flex: 1 1 200px;
}

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
</style>
