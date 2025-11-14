<template>
  <section class="landing-hero">
    <div class="landing-hero__content">
      <h1 class="landing-hero__title">{{ texts.title }}</h1>
      <p class="landing-hero__subtitle">{{ texts.subtitle }}</p>
      <form class="landing-hero__composer" @submit.prevent="handleSubmit">
        <div class="landing-hero__card">
          <div class="landing-hero__input-wrap">
            <textarea
              ref="textareaRef"
              v-model="query"
              class="landing-hero__input"
              rows="1"
              :placeholder="texts.placeholder"
            ></textarea>
          </div>
          <div class="landing-hero__controls">
            <button type="button" class="landing-hero__domain" @click="$emit('select-domain')">
              <span class="landing-hero__domain-icon" aria-hidden="true">＋</span>
              <span class="landing-hero__domain-text">{{ texts.domain }}</span>
              <span class="landing-hero__domain-caret" aria-hidden="true">▾</span>
            </button>
            <button class="landing-hero__submit" type="submit" :disabled="!canSubmit">{{ texts.submit }}</button>
          </div>
        </div>
      </form>
      <div class="landing-hero__actions">
        <button type="button" class="landing-hero__history" @click="$emit('show-history')">
          {{ texts.history }}
        </button>
      </div>
    </div>
  </section>
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
  }
});

const emit = defineEmits(['update:modelValue', 'submit', 'show-history', 'select-domain']);

const query = ref(props.modelValue);
const canSubmit = computed(() => Boolean(query.value?.trim()));
const textareaRef = ref(null);

watch(
  () => props.modelValue,
  (value) => {
    if (value !== query.value) {
      query.value = value;
      nextTick(adjustTextareaHeight);
    }
  }
);

watch(query, (value) => {
  emit('update:modelValue', value);
  nextTick(adjustTextareaHeight);
});

function handleSubmit() {
  const value = query.value?.trim() || '';
  if (!value) {
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
.landing-hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem 1.5rem 6rem;
  background: linear-gradient(180deg, #f4f7ff 0%, #ffffff 45%, #eef2ff 100%);
}

.landing-hero__content {
  width: min(720px, 100%);
  text-align: center;
  background-color: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  padding: 3rem 2.5rem;
  border-radius: 24px;
  box-shadow: 0 24px 48px rgba(15, 46, 94, 0.08);
}

.landing-hero__title {
  margin: 0 0 0.75rem;
  font-size: 2.5rem;
  font-weight: 700;
  color: #1c2754;
}

.landing-hero__subtitle {
  margin: 0 0 2.5rem;
  font-size: 1.1rem;
  color: #4c5c8b;
}


.landing-hero__composer {
  margin: 0;
  width: 100%;
}

.landing-hero__card {
  display: flex;
  flex-direction: column;
  background-color: #fff;
  padding: 1rem 1rem 1rem 1.5rem;
  border-radius: 28px;
  box-shadow: inset 0 0 0 1px rgba(162, 177, 255, 0.6), 0 18px 46px rgba(29, 56, 147, 0.12);
  gap: 1rem;
}

.landing-hero__input-wrap {
  display: flex;
}

.landing-hero__input {
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

.landing-hero__controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(189, 201, 255, 0.6);
}

.landing-hero__domain {
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

.landing-hero__domain:hover {
  background: rgba(204, 212, 255, 0.95);
  transform: translateY(-1px);
}

.landing-hero__domain-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.landing-hero__domain-text {
  line-height: 1;
}

.landing-hero__domain-caret {
  font-size: 0.85rem;
  color: #3550ff;
  transform: translateY(1px);
}

.landing-hero__submit {
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

.landing-hero__submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.28);
}

.landing-hero__submit:disabled {
  cursor: not-allowed;
  opacity: 0.65;
  box-shadow: none;
}

.landing-hero__submit:disabled:hover {
  transform: none;
  box-shadow: none;
}

.landing-hero__actions {
  margin-top: 1.75rem;
}

.landing-hero__history {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #cdd5ff;
  font-size: 0.95rem;
  color: #4866ff;
  font-weight: 600;
  cursor: pointer;
  padding: 0.55rem 1.5rem;
  border-radius: 16px;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  box-shadow: 0 6px 16px rgba(72, 102, 255, 0.12);
}

.landing-hero__history:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(72, 102, 255, 0.18);
}

@media (max-width: 600px) {
  .landing-hero__content {
    padding: 2.25rem 1.75rem;
  }

  .landing-hero__card {
    padding: 1rem;
  }

  .landing-hero__controls {
    flex-direction: column;
    align-items: stretch;
  }

  .landing-hero__domain,
  .landing-hero__submit {
    width: 100%;
    justify-content: center;
  }
}
</style>
