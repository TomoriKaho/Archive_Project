<template>
  <div id="app">
    <ToastContainer />
    <component :is="layoutComponent">
      <RouterView />
    </component>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute, RouterView } from 'vue-router';

import AuthLayout from './layouts/AuthLayout.vue';
import AppLayout from './layouts/AppLayout.vue';
import ToastContainer from './components/ToastContainer.vue';

const route = useRoute();

const layoutComponent = computed(() =>
  route.meta.layout === 'auth' ? AuthLayout : AppLayout
);
</script>
