<template>
  <section class="dashboard">
    <div class="dashboard__header">
      <h2>Hello, {{ user?.name || 'Explorer' }}</h2>
      <p>Here's what's happening with your knowledge base today.</p>
    </div>

    <div class="dashboard__grid">
      <div class="card">
        <h3>Profile</h3>
        <ul class="profile-list">
          <li>
            <span>Name</span><span>{{ user?.name }}</span>
          </li>
          <li>
            <span>Email</span><span>{{ user?.email }}</span>
          </li>
          <li>
            <span>Role</span><span class="tag">{{ user?.role }}</span>
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>Recent Activity</h3>
        <ul class="activity-list">
          <li v-if="recentDocuments.length === 0" class="activity-list__empty">
            No recent documents.
          </li>
          <li v-for="document in recentDocuments" :key="document.id">
            <span class="activity-list__title">{{ document.title }}</span>
            <span class="activity-list__meta"
              >Updated
              {{ formatDate(document.updated_at || document.created_at) }}</span
            >
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>Quick Links</h3>
        <div class="quick-links">
          <RouterLink class="quick-link" :to="{ name: 'documents' }"
            >Manage Documents</RouterLink
          >
          <RouterLink class="quick-link" :to="{ name: 'chat' }"
            >Open Chat</RouterLink
          >
          <RouterLink
            v-if="isAdmin"
            class="quick-link"
            :to="{ name: 'domains' }"
            >Domains</RouterLink
          >
          <RouterLink v-if="isAdmin" class="quick-link" :to="{ name: 'users' }"
            >Users</RouterLink
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';

import { useAuthStore } from '@/store/auth';
import { useDocumentsStore } from '@/store/documents';

const authStore = useAuthStore();
const documentsStore = useDocumentsStore();

const user = computed(() => authStore.user);
const isAdmin = computed(() => authStore.isAdmin);
const recentDocuments = computed(() => documentsStore.items.slice(0, 5));

onMounted(() => {
  documentsStore.loadDocuments({ limit: 5 });
});

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}
</script>

<style scoped>
.dashboard__header h2 {
  margin: 0;
  font-size: 28px;
  color: #111827;
}

.dashboard__header p {
  margin: 8px 0 24px;
  color: #6b7280;
}

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.card {
  background-color: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.card h3 {
  margin-top: 0;
  font-size: 18px;
}

.profile-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-list li {
  display: flex;
  justify-content: space-between;
  color: #374151;
}

.profile-list span:first-child {
  color: #6b7280;
}

.tag {
  background-color: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.activity-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-list__title {
  font-weight: 600;
  color: #111827;
}

.activity-list__meta {
  color: #6b7280;
  font-size: 13px;
}

.activity-list__empty {
  color: #9ca3af;
}

.quick-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border-radius: 10px;
  background: #f3f4f6;
  color: #1f2937;
  text-decoration: none;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.quick-link:hover {
  background: #e5e7eb;
}
</style>
