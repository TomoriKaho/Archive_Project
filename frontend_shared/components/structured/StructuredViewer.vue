<template>
  <div v-if="blocks.length" class="structured-viewer">
    <StructuredBlockItem
      v-for="(block, index) in blocks"
      :key="`block-${index}`"
      :block="block"
      :indent-step="indentStep"
      :highlight-tokens="highlightTokens"
    />
  </div>
  <div v-else class="structured-viewer structured-viewer--plain">
    <HighlightedText :text="fallbackText" :tokens="highlightTokens" />
  </div>
</template>

<script setup lang="js">
import { computed, defineComponent, h } from 'vue';

import { INDENT_STEP, buildBlocksFromValue, formatPrimitive, isObjectLike, parseStructuredValue } from './structuredUtils';

const props = defineProps({
  value: {
    type: [String, Number, Boolean, Object, Array],
    default: ''
  },
  indent: {
    type: Number,
    default: INDENT_STEP
  },
  highlightTokens: {
    type: Array,
    default: () => []
  }
});

const parsedValue = computed(() => parseStructuredValue(props.value));

const blocks = computed(() => {
  const value = parsedValue.value;
  if (isObjectLike(value) || Array.isArray(value)) {
    return buildBlocksFromValue(value);
  }
  return [];
});

const fallbackText = computed(() => formatPrimitive(parsedValue.value));
const indentStep = computed(() => (Number.isFinite(props.indent) ? props.indent : INDENT_STEP));

const HighlightedText = defineComponent({
  name: 'StructuredViewerHighlightedText',
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
            ? h('mark', { class: 'structured-viewer__highlight', key: segment.key || `mark-${index}` }, segment.text)
            : h('span', { key: segment.key || `text-${index}` }, segment.text)
        )
      );
  }
});

const StructuredBlockItem = defineComponent({
  name: 'StructuredBlockItem',
  props: {
    block: {
      type: Object,
      required: true
    },
    indentStep: {
      type: Number,
      required: true
    },
    highlightTokens: {
      type: Array,
      default: () => []
    }
  },
  setup(childProps) {
    return () => {
      const block = childProps.block;
      const hasChildren = Array.isArray(block.children) && block.children.length > 0;

      return h(
        'div',
        {
          class: 'structured-block',
          style: { paddingLeft: `${block.depth * childProps.indentStep}px` }
        },
        [
          h(
            'div',
            { class: 'structured-block__name' },
            h(HighlightedText, { text: block.label || '[value]', tokens: childProps.highlightTokens })
          ),
          block.valueText !== undefined && block.valueText !== ''
            ? h(
                'div',
                { class: 'structured-block__value' },
                h(HighlightedText, { text: block.valueText, tokens: childProps.highlightTokens })
              )
            : null,
          hasChildren
            ? block.children.map((child, index) =>
                h(StructuredBlockItem, {
                  block: child,
                  indentStep: childProps.indentStep,
                  key: `child-${index}`,
                  highlightTokens: childProps.highlightTokens
                })
              )
            : null
        ].filter(Boolean)
      );
    };
  }
});
</script>

<style scoped>
.structured-viewer {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.structured-viewer--plain {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
}

.structured-block {
  margin-bottom: 14px;
}

.structured-block:last-child {
  margin-bottom: 0;
}

.structured-block__name {
  font-weight: 700;
  font-size: 16px;
  line-height: 1.35;
}

.structured-block__value {
  font-weight: 400;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  margin-top: 2px;
}

.structured-viewer__highlight {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0 2px;
  border-radius: 3px;
}
</style>
