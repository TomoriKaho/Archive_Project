<template>
  <form class="query-composer" @submit.prevent="handleSubmit">
    <div class="query-composer__card">
      <div class="query-composer__input-wrap">
        <textarea
          ref="textareaRef"
          v-model="draft"
          class="query-composer__input"
          rows="1"
          :placeholder="texts.placeholder"
        ></textarea>
      </div>
      <div class="query-composer__controls">
        <div v-if="domains.length" class="query-composer__domains">
          <button type="button" class="query-composer__domains-button" @click="toggleDomains">
            <span class="query-composer__domains-icon" aria-hidden="true">＋</span>
            <span class="query-composer__domains-label">{{ texts.domainButton }}</span>
            <span v-if="selectedDomainsCount" class="query-composer__domains-badge">{{ domainBadge }}</span>
            <span class="query-composer__domains-caret" aria-hidden="true">▾</span>
          </button>
          <transition name="query-composer-fade">
            <div v-if="domainsPanelOpen" class="query-composer__domains-panel">
              <p class="query-composer__domains-hint">{{ texts.domainHint }}</p>
              <div class="query-composer__domains-grid">
                <label v-for="domain in domains" :key="domain.id" class="query-composer__domains-option">
                  <input
                    type="checkbox"
                    :value="domain.id"
                    :checked="pendingSelection.has(domain.id)"
                    @change="toggleDomain(domain.id)"
                  />
                  <span>{{ domain.name }}</span>
                </label>
              </div>
              <div class="query-composer__domains-actions">
                <button type="button" class="query-composer__domains-apply" @click="applyDomains">
                  {{ texts.domainApply }}
                </button>
                <button type="button" class="query-composer__domains-clear" @click="clearDomains">
                  {{ texts.domainClear }}
                </button>
              </div>
            </div>
          </transition>
        </div>
        <button class="query-composer__submit" type="submit" :disabled="!canSubmit || submitting">
          {{ submitting ? texts.submitting : texts.submit }}
        </button>
      </div>
    </div>
  </form>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  texts: {
    type: Object,
    required: true
  },
  domains: {
    type: Array,
    default: () => []
  },
  selectedDomains: {
    type: Array,
    default: () => []
  },
  submitting: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'submit', 'update:domains']);

const draft = ref(props.modelValue);
const textareaRef = ref(null);
const domainsPanelOpen = ref(false);
const pendingSelection = ref(new Set(props.selectedDomains));

watch(
  () => props.modelValue,
  (value) => {
    if (value !== draft.value) {
      draft.value = value;
      nextTick(adjustTextareaHeight);
    }
  }
);

watch(draft, (value) => {
  emit('update:modelValue', value);
  nextTick(adjustTextareaHeight);
});

watch(
  () => props.selectedDomains,
  (value) => {
    pendingSelection.value = new Set(value);
  }
);

const canSubmit = computed(() => Boolean(draft.value?.trim()));

const selectedDomainsCount = computed(() => pendingSelection.value.size);

const domainBadge = computed(() => {
  const count = selectedDomainsCount.value;
  if (!count) {
    return '';
  }
  const badge = props.texts?.domainBadge;
  if (typeof badge === 'function') {
    return badge(count);
  }
  if (typeof badge === 'string') {
    return badge.replace('{count}', count);
  }
  return count.toString();
});

function toggleDomains() {
  domainsPanelOpen.value = !domainsPanelOpen.value;
}

function toggleDomain(id) {
  const numericId = Number(id);
  const next = new Set(pendingSelection.value);
  if (next.has(numericId)) {
    next.delete(numericId);
  } else {
    next.add(numericId);
  }
  pendingSelection.value = next;
}

function applyDomains() {
  emit('update:domains', Array.from(pendingSelection.value));
  domainsPanelOpen.value = false;
}

function clearDomains() {
  pendingSelection.value = new Set();
  emit('update:domains', []);
}

function handleSubmit() {
  const value = draft.value?.trim() || '';
  if (!value || props.submitting) {
    return;
  }
  emit('submit', value);
}

function adjustTextareaHeight() {
  const el = textareaRef.value;
  if (!el) {
    return;
  }
  el.style.height = 'auto';
  el.style.height = `${el.scrollHeight}px`;
}

onMounted(() => {
  nextTick(adjustTextareaHeight);
});
</script>

<style scoped lang="scss">
.query-composer {
  margin: 0;
  width: 100%;
}

.query-composer__card {
  display: flex;
  flex-direction: column;
  background-color: #fff;
  padding: 1rem 1rem 1rem 1.5rem;
  border-radius: 28px;
  box-shadow: inset 0 0 0 1px rgba(162, 177, 255, 0.6), 0 18px 46px rgba(29, 56, 147, 0.12);
  gap: 1rem;
}

.query-composer__input-wrap {
  display: flex;
}

.query-composer__input {
  width: 100%;
  border: none;
  font-size: 1.05rem;
  outline: none;
  background: transparent;
  color: #1a1a1a;
  resize: none;
  line-height: 1.6;
  min-height: 3rem;
  max-height: 12rem;
  overflow-y: auto;
  font-family: inherit;
  padding: 0;
}

.query-composer__controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(189, 201, 255, 0.6);
}

.query-composer__domains {
  position: relative;
  display: inline-flex;
}

.query-composer__domains-button {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: none;
  background: rgba(230, 234, 255, 0.75);
  color: #3550ff;
  font-weight: 600;
  font-size: 0.95rem;
  border-radius: 18px;
  padding: 0.65rem 1.1rem;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.query-composer__domains-button:hover {
  background: rgba(204, 212, 255, 0.95);
  transform: translateY(-1px);
}

.query-composer__domains-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.query-composer__domains-label {
  line-height: 1;
}

.query-composer__domains-caret {
  font-size: 0.85rem;
  color: #3550ff;
  transform: translateY(1px);
}

.query-composer__domains-badge {
  background: #3550ff;
  color: #fff;
  border-radius: 12px;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
}

.query-composer__domains-panel {
  position: absolute;
  left: 0;
  top: 110%;
  width: 320px;
  max-height: 360px;
  overflow-y: auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 18px 40px rgba(26, 40, 90, 0.15);
  padding: 1rem 1.25rem 1.25rem;
  z-index: 10;
}

.query-composer__domains-hint {
  margin: 0 0 0.75rem;
  color: #6f7dae;
  font-size: 0.85rem;
}

.query-composer__domains-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.query-composer__domains-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  border-radius: 10px;
  transition: background-color 0.2s ease;
}

.query-composer__domains-option:hover {
  background-color: rgba(74, 92, 200, 0.08);
}

.query-composer__domains-option input {
  accent-color: #4a5cc8;
}

.query-composer__domains-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.query-composer__domains-apply {
  border: none;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  font-weight: 600;
  padding: 0.45rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
}

.query-composer__domains-clear {
  border: none;
  background: none;
  color: #8a95c7;
  font-weight: 600;
  cursor: pointer;
}

.query-composer__submit {
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.85rem;
  font-size: 1rem;
  font-weight: 600;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
}

.query-composer__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.28);
}

.query-composer__submit:disabled {
  cursor: not-allowed;
  opacity: 0.65;
  box-shadow: none;
}

.query-composer-fade-enter-active,
.query-composer-fade-leave-active {
  transition: opacity 0.15s ease;
}

.query-composer-fade-enter-from,
.query-composer-fade-leave-to {
  opacity: 0;
}

@media (max-width: 600px) {
  .query-composer__card {
    padding: 1rem;
  }

  .query-composer__controls {
    flex-direction: column;
    align-items: stretch;
  }

  .query-composer__domains-button,
  .query-composer__submit {
    width: 100%;
    justify-content: center;
  }

  .query-composer__domains-panel {
    left: 50%;
    transform: translateX(-50%);
  }
}
</style>
