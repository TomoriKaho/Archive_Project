<template>
  <div class="tabs">
    <div class="tabs__headers">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="tabs__tab"
        :class="{ 'tabs__tab--active': tab.value === modelValue }"
        @click="select(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="tabs__content">
      <slot :active="modelValue" />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  tabs: {
    type: Array,
    required: true
  },
  modelValue: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:modelValue']);

function select(value) {
  emit('update:modelValue', value);
}
</script>

<style scoped>
.tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tabs__headers {
  display: flex;
  gap: 12px;
}

.tabs__tab {
  flex: 1;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: #f3f4f6;
  cursor: pointer;
  font-weight: 600;
}

.tabs__tab--active {
  background: #1f2937;
  color: #ffffff;
}
</style>
