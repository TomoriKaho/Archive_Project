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
        <h3>{{ t('dashboard.quickLinks.title') }}</h3>
        <div class="quick-links">
          <RouterLink class="quick-link" :to="{ name: 'chat' }">
            <span class="quick-link__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M2.25 12.75c0 1.2.912 2.25 2.1 2.25H6v3l3-3h5.4c1.188 0 2.1-1.05 2.1-2.25V5.25C16.5 4.05 15.588 3 14.4 3H4.35C3.162 3 2.25 4.05 2.25 5.25v7.5z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M17.25 8.25h1.65c1.188 0 2.1 1.05 2.1 2.25v5.25c0 1.2-.912 2.25-2.1 2.25H18v3l-3-3"
                />
              </svg>
            </span>
            <span>{{ t('dashboard.quickLinks.chat') }}</span>
          </RouterLink>
          <RouterLink
            v-if="isAdmin"
            class="quick-link"
            :to="{ name: 'domains' }"
          >
            <span class="quick-link__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 21a9 9 0 100-18 9 9 0 000 18zm3.75-9a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 3v2.25M12 18.75V21"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 12h2.25M18.75 12H21"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M5.197 5.197l1.591 1.591M17.212 17.212l1.591 1.591"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M5.197 18.803l1.591-1.591M17.212 6.788l1.591-1.591"
                />
              </svg>
            </span>
            <span>{{ t('dashboard.quickLinks.domains') }}</span>
          </RouterLink>
          <RouterLink class="quick-link" :to="{ name: 'documents' }">
            <span class="quick-link__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 5.25V4.5A1.5 1.5 0 0110.5 3h6A1.5 1.5 0 0118 4.5v15a1.5 1.5 0 01-1.5 1.5h-6A1.5 1.5 0 019 19.5v-.75"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 5.25H6A1.5 1.5 0 004.5 6.75v10.5A1.5 1.5 0 006 18.75h3"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 8.25h3.75M12 12h3.75M12 15.75h3.75"
                />
              </svg>
            </span>
            <span>{{ t('dashboard.quickLinks.documents') }}</span>
          </RouterLink>
          <RouterLink v-if="isAdmin" class="quick-link" :to="{ name: 'users' }">
            <span class="quick-link__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975M15.75 7.5a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M18.75 21a4.5 4.5 0 00-9 0"
                />
              </svg>
            </span>
            <span>{{ t('dashboard.quickLinks.users') }}</span>
          </RouterLink>
        </div>
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
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  padding: 12px 16px;
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

.quick-link__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.quick-link__icon svg {
  width: 20px;
  height: 20px;
}
</style>
