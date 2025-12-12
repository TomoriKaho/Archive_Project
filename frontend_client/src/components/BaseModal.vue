<template>
  <Teleport v-if="canTeleport" to="body">
    <transition name="modal">
      <div v-if="modelValue" class="modal-overlay" @click.self="onOverlayClick">
        <div class="modal">
          <header class="modal__header">
            <h3>{{ title }}</h3>
            <button type="button" class="modal__close" @click="close">×</button>
          </header>
          <div class="modal__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  modelValue: {
    type: Boolean,
    required: true
  },
  closeOnOverlay: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:modelValue']);

const canTeleport = ref(false);

onMounted(() => {
  canTeleport.value = true;
});

onBeforeUnmount(() => {
  canTeleport.value = false;
});

function close() {
  emit('update:modelValue', false);
}

function onOverlayClick() {
  if (props.closeOnOverlay) {
    close();
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal {
  background: #ffffff;
  border-radius: 16px;
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 32px 64px rgba(15, 23, 42, 0.25);
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal__body {
  padding: 24px;
  overflow-y: auto;
}

.modal__footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.modal__close {
  background: transparent;
  border: none;
  font-size: 24px;
  cursor: pointer;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
