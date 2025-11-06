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

import AppSidebar from '@/components/AppSidebar.vue';
import AppTopbar from '@/components/AppTopbar.vue';
import { useUiStore } from '@/store/ui';

const route = useRoute();
const uiStore = useUiStore();

const title = computed(() => route.meta.title || 'Archive AI');
</script>

<style scoped>
.content-area {
  padding: 24px;
  flex: 1;
  min-height: calc(100vh - 64px);
  background: #f5f6fa;
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
