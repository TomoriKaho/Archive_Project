<template>
  <section class="landing-hero">
    <div class="landing-hero__content">
      <h1 class="landing-hero__title">{{ texts.title }}</h1>
      <p class="landing-hero__subtitle">{{ texts.subtitle }}</p>
      <QueryComposer
        v-model="query"
        :texts="texts.composer"
        :domains="domains"
        :selected-domains="selectedDomains"
        :submitting="submitting"
        @submit="handleSubmit"
        @update:domains="updateDomains"
      />
      <div class="landing-hero__actions">
        <button type="button" class="landing-hero__history" @click="$emit('show-history')">
          {{ texts.history }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue';
import QueryComposer from '@/components/QueryComposer.vue';

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

const emit = defineEmits(['update:modelValue', 'submit', 'show-history', 'update:domains']);

const query = ref(props.modelValue);

watch(
  () => props.modelValue,
  (value) => {
    if (value !== query.value) {
      query.value = value;
    }
  }
);

watch(query, (value) => {
  emit('update:modelValue', value);
});

function handleSubmit(value) {
  emit('submit', value);
}

function updateDomains(domainIds) {
  emit('update:domains', domainIds);
}
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
}
</style>
