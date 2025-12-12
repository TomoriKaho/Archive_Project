<template>
  <div class="tree-node">
    <template v-if="Array.isArray(value)">
      <ol class="tree-node__list tree-node__list--ordered">
        <li v-for="(item, index) in value" :key="index">
          <ArchiveTreeNode :value="item" :highlight-tokens="highlightTokens" />
        </li>
      </ol>
    </template>
    <template v-else-if="isPlainObject(value)">
      <ul class="tree-node__list">
        <li v-for="(val, key) in value" :key="key">
          <HighlightedText class="tree-node__key" :text="`${key}:`" :tokens="highlightTokens" />
          <ArchiveTreeNode :value="val" :highlight-tokens="highlightTokens" />
        </li>
      </ul>
    </template>
    <template v-else>
      <HighlightedText class="tree-node__value" :text="formatValue(value)" :tokens="highlightTokens" />
    </template>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, useAttrs } from 'vue';

function isPlainObject(target) {
  return target && typeof target === 'object' && !Array.isArray(target);
}

const props = defineProps({
  value: {
    type: [Object, Array, String, Number, Boolean, null],
    default: null
  },
  highlightTokens: {
    type: Array,
    default: () => []
  }
});

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
    const attrs = useAttrs();
    const matcher = computed(() => buildMatcher(highlightProps.tokens));

    function buildMatcher(tokens = []) {
      const normalized = tokens
        .map((token) => (token === null || token === undefined ? '' : String(token).trim()))
        .filter(Boolean);
      if (!normalized.length) return null;
      return new RegExp(`(${normalized.map((token) => escapeRegExp(token)).join('|')})`, 'gi');
    }

    function escapeRegExp(text) {
      return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    return () => {
      const content =
        highlightProps.text === null || highlightProps.text === undefined
          ? ''
          : String(highlightProps.text);
      const highlightMatcher = matcher.value;

      const baseProps = { ...attrs, class: [highlightProps.class, attrs.class] };

      if (!content || !highlightMatcher) {
        return h('span', baseProps, content);
      }

      const segmentMatcher = new RegExp(highlightMatcher.source, 'gi');
      const strictMatcher = new RegExp(`^${highlightMatcher.source}$`, 'i');
      const segments = content.split(segmentMatcher);

      return h(
        'span',
        baseProps,
        segments
          .filter((part) => part !== '')
          .map((part, index) =>
            strictMatcher.test(part)
              ? h('mark', { class: 'tree-highlight', key: `mark-${index}` }, part)
              : h('span', { key: `text-${index}` }, part)
          )
      );
    };
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

.tree-highlight {
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 4px;
  padding: 0 2px;
}
</style>
