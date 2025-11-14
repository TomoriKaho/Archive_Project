<template>
  <section class="landing-hero">
    <div class="landing-hero__content">
      <h1 class="landing-hero__title">{{ texts.title }}</h1>
      <p class="landing-hero__subtitle">{{ texts.subtitle }}</p>
      <form class="landing-hero__form" @submit.prevent="handleSubmit">
        <textarea
          ref="textareaRef"
          v-model="query"
          class="landing-hero__input"
          rows="1"
          :placeholder="texts.placeholder"
        ></textarea>
        <button class="landing-hero__submit" type="submit" :disabled="!canSubmit">{{ texts.submit }}</button>
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

const emit = defineEmits(['update:modelValue', 'submit', 'show-history']);

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


.landing-hero__form {
  display: flex;
  gap: 0.75rem;
  align-items: stretch;
  background-color: #fff;
  padding: 0.75rem 0.75rem 0.75rem 1.25rem;
  border-radius: 24px;
  box-shadow: inset 0 0 0 1px #d9e1ff;
}

.landing-hero__input {
  flex: 1;
  border: none;
  font-size: 1rem;
  outline: none;
  background: transparent;
  color: #1a1a1a;
  resize: none;
  line-height: 1.5;
  min-height: 2.75rem;
  max-height: 10rem;
  overflow-y: auto;
  font-family: inherit;
  padding: 0;
}

.landing-hero__submit {
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.75rem;
  font-size: 1rem;
  font-weight: 600;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
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

  .landing-hero__form {
    flex-direction: column;
    border-radius: 20px;
    padding: 0.75rem 0.75rem 0.95rem;
  }

  .landing-hero__submit {
    width: 100%;
  }
}
</style>
