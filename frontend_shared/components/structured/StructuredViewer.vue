<template>
  <div v-if="blocks.length" class="structured-viewer">
    <StructuredBlockItem
      v-for="(block, index) in blocks"
      :key="`block-${index}`"
      :block="block"
      :indent-step="indentStep"
    />
  </div>
  <div v-else class="structured-viewer structured-viewer--plain">
    {{ fallbackText }}
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
          h('div', { class: 'structured-block__name' }, block.label || '[value]'),
          block.valueText !== undefined && block.valueText !== ''
            ? h('div', { class: 'structured-block__value' }, block.valueText)
            : null,
          hasChildren
            ? block.children.map((child, index) =>
                h(StructuredBlockItem, {
                  block: child,
                  indentStep: childProps.indentStep,
                  key: `child-${index}`
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
</style>
