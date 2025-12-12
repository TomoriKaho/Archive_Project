<template>
  <div class="archive-tree__node" :style="{ marginLeft: `${depth * indent}px` }">
    <div class="archive-tree__header">
      <div class="archive-tree__title">{{ titleText }}</div>
      <div v-if="metaItems.length" class="archive-tree__meta">
        <span v-for="(meta, index) in metaItems" :key="`meta-${index}`" class="archive-tree__meta-item">
          {{ meta }}
        </span>
      </div>
    </div>
    <details v-if="node.scopecontent" class="archive-tree__scope">
      <summary class="archive-tree__scope-summary">{{ expandLabel }}</summary>
      <div class="archive-tree__scope-body">{{ node.scopecontent }}</div>
    </details>
    <ArchiveTreeNode
      v-for="(child, childIndex) in childNodes"
      :key="`child-${childIndex}`"
      :node="child"
      :depth="depth + 1"
      :indent="indent"
      :expand-label="expandLabel"
    />
  </div>
</template>

<script setup lang="js">
import { computed } from 'vue';

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  depth: {
    type: Number,
    default: 0
  },
  indent: {
    type: Number,
    default: 14
  },
  expandLabel: {
    type: String,
    default: '展开'
  }
});

const metaItems = computed(() => [props.node.date, props.node.extent].filter(Boolean));
const childNodes = computed(() => (Array.isArray(props.node.children) ? props.node.children : []));
const titleText = computed(() => [props.node.unitid, props.node.title].filter(Boolean).join(' ').trim() || '未命名节点');
</script>

<style scoped>
.archive-tree__node {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.archive-tree__header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.archive-tree__title {
  font-weight: 700;
  color: #111827;
}

.archive-tree__meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.archive-tree__meta-item {
  background: #eef2ff;
  color: #4338ca;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
}

.archive-tree__scope {
  margin: 4px 0 0;
}

.archive-tree__scope-summary {
  cursor: pointer;
  color: #2563eb;
  font-weight: 600;
  display: inline-block;
  margin-bottom: 8px;
}

.archive-tree__scope-body {
  margin-top: 6px;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 8px;
  line-height: 1.5;
}
</style>
