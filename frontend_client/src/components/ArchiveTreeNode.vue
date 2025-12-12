<template>
  <div class="tree-node">
    <template v-if="Array.isArray(value)">
      <ol class="tree-node__list tree-node__list--ordered">
        <li v-for="(item, index) in value" :key="index">
          <ArchiveTreeNode :value="item" />
        </li>
      </ol>
    </template>
    <template v-else-if="isPlainObject(value)">
      <ul class="tree-node__list">
        <li v-for="(val, key) in value" :key="key">
          <span class="tree-node__key">{{ key }}:</span>
          <ArchiveTreeNode :value="val" />
        </li>
      </ul>
    </template>
    <template v-else>
      <span class="tree-node__value">{{ formatValue(value) }}</span>
    </template>
  </div>
</template>

<script setup>
function isPlainObject(target) {
  return target && typeof target === 'object' && !Array.isArray(target);
}

defineProps({
  value: {
    type: [Object, Array, String, Number, Boolean, null],
    default: null
  }
});

function formatValue(val) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? 'true' : 'false';
  if (typeof val === 'number') return val;
  if (typeof val === 'string') return val;
  try {
    return JSON.stringify(val);
  } catch (error) {
    return String(val);
  }
}
</script>

<style scoped>
.tree-node__list {
  margin: 0;
  padding-left: 1rem;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tree-node__list--ordered {
  list-style: decimal;
}

.tree-node__key {
  font-weight: 700;
  margin-right: 6px;
  color: #0f172a;
}

.tree-node__value {
  color: #1f2937;
}
</style>
