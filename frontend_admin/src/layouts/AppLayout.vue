<template>
  <div
    :class="[
      'app-shell',
      { 'app-shell--collapsed': uiStore.isSidebarCollapsed }
    ]"
  >
    <AppSidebar :collapsed="uiStore.isSidebarCollapsed" />
    <div class="main">
      <AppTopbar :title="title" @toggle-sidebar="uiStore.toggleSidebar" />
      <main class="content-area">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';

import AppSidebar from '@/components/AppSidebar.vue';
import AppTopbar from '@/components/AppTopbar.vue';
import { useUiStore } from '@/store/ui';

const route = useRoute();
const uiStore = useUiStore();
const { t } = useI18n();

const title = computed(() =>
  route.meta.titleKey ? t(route.meta.titleKey) : t('app.name')
);
</script>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.content-area {
  padding: 24px;
  flex: 1;
  min-height: calc(100vh - 64px);
  background: #f5f6fa;
  min-width: 0;
  overflow-x: hidden;
}

@media (max-width: 960px) {
  .app-shell {
    flex-direction: column;
  }

  .content-area {
    min-height: auto;
  }
}
</style>
