<template>
  <div v-if="normalizedNodes.length" class="archive-tree">
    <div
      v-for="(node, index) in normalizedNodes"
      :key="`node-${index}`"
      class="archive-tree__node"
      :style="{ marginLeft: `${indentStep * 0}px` }"
    >
      <ArchiveTreeNode
        :node="node"
        :depth="0"
        :indent="indentStep"
        :expand-label="expandLabel"
        :highlight-tokens="highlightTokens"
      />
    </div>
  </div>
  <div v-else class="archive-tree archive-tree--empty">{{ emptyText }}</div>
</template>

<script setup lang="js">
import { computed } from 'vue';

import { INDENT_STEP, normalizeArchiveNodes, parseStructuredValue } from './structuredUtils';
import ArchiveTreeNode from './ArchiveTreeNode.vue';

const props = defineProps({
  value: { type: [Object, Array, String], default: null },
  expandLabel: {
    type: String,
    default: '展开'
  },
  highlightTokens: {
    type: Array,
    default: () => []
  },
  emptyText: {
    type: String,
    default: '—'
  },
  indent: {
    type: Number,
    default: INDENT_STEP
  }
});

const normalizedNodes = computed(() => normalizeArchiveNodes(parseStructuredValue(props.value)));
const indentStep = computed(() => (Number.isFinite(props.indent) ? props.indent : INDENT_STEP));
</script>

<style scoped>
.archive-tree {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
}

.archive-tree__node {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.archive-tree--empty {
  color: #6b7280;
}
</style>
