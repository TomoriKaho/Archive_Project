<template>
  <div class="toast-container">
    <transition-group name="toast" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
      >
        <span>{{ toast.message }}</span>
        <button type="button" class="toast__close" @click="remove(toast.id)">
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia';

import { useUiStore } from '@/store/ui';

const uiStore = useUiStore();
const { toasts } = storeToRefs(uiStore);

function remove(id) {
  uiStore.removeToast(id);
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 9999;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  min-width: 260px;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.15);
  color: #ffffff;
}

.toast--success {
  background-color: #10b981;
}

.toast--error {
  background-color: #ef4444;
}

.toast--warning {
  background-color: #f59e0b;
}

.toast--info {
  background-color: #3b82f6;
}

.toast__close {
  background: transparent;
  border: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
