<template>
  <section class="dashboard">
    <div class="dashboard__header">
      <h2>
        {{
          displayName
            ? t('dashboard.greetingNamed', { name: displayName })
            : t('dashboard.greetingUnnamed')
        }}
      </h2>
      <p>{{ t('dashboard.subtitle') }}</p>
    </div>

    <div class="dashboard__grid">
      <div class="card">
        <h3>{{ t('dashboard.profile.title') }}</h3>
        <ul class="profile-list">
          <li>
            <span>{{ t('dashboard.profile.name') }}</span
            ><span>{{ displayName || '—' }}</span>
          </li>
          <li>
            <span>{{ t('dashboard.profile.email') }}</span
            ><span>{{ user?.email }}</span>
          </li>
          <li>
            <span>{{ t('dashboard.profile.role') }}</span>
            <span class="tag">
              {{ user?.is_admin ? t('roles.admin') : t('roles.member') }}
            </span>
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>{{ t('dashboard.recentActivity.title') }}</h3>
        <ul class="activity-list">
          <li v-if="recentDocuments.length === 0" class="activity-list__empty">
            {{ t('dashboard.recentActivity.empty') }}
          </li>
          <li v-for="document in recentDocuments" :key="document.id">
            <span class="activity-list__title">{{ document.title }}</span>
            <span class="activity-list__meta"
              >{{
                t('dashboard.recentActivity.updated', {
                  date: formatDate(document.updated_at || document.created_at)
                })
              }}</span
            >
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>{{ t('dashboard.quickLinks.title') }}</h3>
        <div class="quick-links">
          <RouterLink class="quick-link" :to="{ name: 'documents' }"
            >{{ t('dashboard.quickLinks.documents') }}</RouterLink
          >
          <RouterLink class="quick-link" :to="{ name: 'chat' }"
            >{{ t('dashboard.quickLinks.chat') }}</RouterLink
          >
          <RouterLink
            v-if="isAdmin"
            class="quick-link"
            :to="{ name: 'domains' }"
            >{{ t('dashboard.quickLinks.domains') }}</RouterLink
          >
          <RouterLink v-if="isAdmin" class="quick-link" :to="{ name: 'users' }"
            >{{ t('dashboard.quickLinks.users') }}</RouterLink
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useI18n } from 'vue-i18n';

import { useAuthStore } from '@/store/auth';
import { useDocumentsStore } from '@/store/documents';

const authStore = useAuthStore();
const documentsStore = useDocumentsStore();
const { t, locale } = useI18n();

const user = computed(() => authStore.user);
const displayName = computed(() => user.value?.full_name || user.value?.email);
const isAdmin = computed(() => authStore.isAdmin);
const recentDocuments = computed(() => documentsStore.items.slice(0, 5));

onMounted(() => {
  documentsStore.loadDocuments({ limit: 5 });
});

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
  margin-left: 8px;
  color: #6b7280;
  display: inline-block;
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
