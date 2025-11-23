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

const emit = defineEmits(['update:modelValue', 'submit', 'update:domains']);

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
  width: 100%;
  padding: 1.5rem;
  position: relative;
  z-index: 1;
}

.landing-hero__content {
  width: min(720px, 100%);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.landing-hero__title {
  margin: 0 0 0.75rem;
  font-size: 2.5rem;
  font-weight: 700;
  color: #1c2754;
}

.landing-hero__subtitle {
  margin: 0;
  font-size: 1.1rem;
  color: #4c5c8b;
}

@media (max-width: 600px) {
  .landing-hero__content {
    padding: 0;
  }
}
</style>
