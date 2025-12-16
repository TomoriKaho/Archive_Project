<template>
  <div class="archive-tree__node" :style="{ marginLeft: `${depth * indent}px` }">
    <div class="archive-tree__header">
      <div class="archive-tree__title">
        <HighlightedText :text="titleText" :tokens="highlightTokens" />
      </div>
      <div v-if="metaItems.length" class="archive-tree__meta">
        <span v-for="(meta, index) in metaItems" :key="`meta-${index}`" class="archive-tree__meta-item">
          <HighlightedText :text="meta" :tokens="highlightTokens" />
        </span>
      </div>
    </div>
    <details v-if="node.scopecontent" class="archive-tree__scope">
      <summary class="archive-tree__scope-summary">{{ expandLabel }}</summary>
      <div class="archive-tree__scope-body">
        <HighlightedText :text="node.scopecontent" :tokens="highlightTokens" />
      </div>
    </details>
    <ArchiveTreeNode
      v-for="(child, childIndex) in childNodes"
      :key="`child-${childIndex}`"
      :node="child"
      :depth="depth + 1"
      :indent="indent"
      :expand-label="expandLabel"
      :highlight-tokens="highlightTokens"
    />
  </div>
</template>

<script setup lang="js">
import { computed, defineComponent, h } from 'vue';

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
  },
  highlightTokens: {
    type: Array,
    default: () => []
  }
});

const metaItems = computed(() => [props.node.date, props.node.extent].filter(Boolean));
const childNodes = computed(() => (Array.isArray(props.node.children) ? props.node.children : []));
const titleText = computed(() => [props.node.unitid, props.node.title].filter(Boolean).join(' ').trim() || '未命名节点');

const HighlightedText = defineComponent({
  name: 'ArchiveNodeHighlightedText',
  props: {
    text: {
      type: [String, Number, Boolean],
      default: ''
    },
    tokens: {
      type: Array,
      default: () => []
    }
  },
  setup(highlightProps) {
    const normalizedTokens = computed(() =>
      Array.from(
        new Set(
          (highlightProps.tokens || [])
            .map((token) => (token === null || token === undefined ? '' : String(token).trim()))
            .filter(Boolean)
            .map((token) => normalizeText(token))
        )
      )
    );

    function normalizeText(text) {
      return text
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
    }

    function findAllMatches(content, token) {
      const matches = [];
      if (!token) return matches;
      let startIndex = 0;
      while (startIndex < content.length) {
        const matchIndex = content.indexOf(token, startIndex);
        if (matchIndex === -1) break;
        matches.push({ start: matchIndex, end: matchIndex + token.length });
        startIndex = matchIndex + token.length;
      }
      return matches;
    }

    function mergeRanges(ranges) {
      if (!ranges.length) return [];
      const merged = [ranges[0]];

      for (let i = 1; i < ranges.length; i += 1) {
        const current = ranges[i];
        const last = merged[merged.length - 1];
        if (current.start <= last.end) {
          last.end = Math.max(last.end, current.end);
        } else {
          merged.push({ ...current });
        }
      }

      return merged;
    }

    function buildSegments(rawText) {
      const content = rawText === null || rawText === undefined ? '' : String(rawText);
      const tokens = normalizedTokens.value;

      if (!content || !tokens.length) {
        return [{ text: content, highlight: false }];
      }

      const normalizedContent = normalizeText(content);
      const matches = tokens
        .flatMap((token) => findAllMatches(normalizedContent, token))
        .sort((a, b) => a.start - b.start || a.end - b.end);
      const merged = mergeRanges(matches);

      if (!merged.length) return [{ text: content, highlight: false }];

      const segments = [];
      let cursor = 0;
      merged.forEach(({ start, end }, index) => {
        if (start > cursor) {
          segments.push({ text: content.slice(cursor, start), highlight: false, key: `pre-${index}` });
        }
        segments.push({ text: content.slice(start, end), highlight: true, key: `mark-${index}` });
        cursor = end;
      });

      if (cursor < content.length) {
        segments.push({ text: content.slice(cursor), highlight: false, key: 'post' });
      }

      return segments;
    }

    return () =>
      h(
        'span',
        buildSegments(highlightProps.text).map((segment, index) =>
          segment.highlight
            ? h('mark', { class: 'archive-tree__highlight', key: segment.key || `mark-${index}` }, segment.text)
            : h('span', { key: segment.key || `text-${index}` }, segment.text)
        )
      );
  }
});
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

.archive-tree__highlight {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0 2px;
  border-radius: 3px;
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
