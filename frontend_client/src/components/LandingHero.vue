<template>
  <section class="landing-hero">
    <div
      class="landing-hero__content"
      :class="{ 'landing-hero__content--domains-open': domainsPanelOpen || lifted }"
    >
      <transition name="landing-hero-fade">
        <h1 v-if="!domainsPanelOpen && !lifted" class="landing-hero__title">{{ texts.title }}</h1>
      </transition>
      <transition name="landing-hero-fade">
        <p v-if="!domainsPanelOpen && !lifted" class="landing-hero__subtitle">{{ texts.subtitle }}</p>
      </transition>
      <QueryComposer
        v-model="query"
        :texts="texts.composer"
        :domains="domains"
        :selected-domains="selectedDomains"
        :submitting="submitting"
        :mode="mode"
        :search-type="searchType"
        @submit="handleSubmit"
        @update:domains="updateDomains"
        @update:mode="updateMode"
        @update:searchType="updateSearchType"
        @domains-panel-toggle="handleDomainsPanelToggle"
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
  },
  mode: {
    type: String,
    default: 'assistant'
  },
  searchType: {
    type: String,
    default: 'precise'
  },
  lifted: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'submit', 'update:domains', 'update:mode', 'update:searchType']);

const query = ref(props.modelValue);
const domainsPanelOpen = ref(false);

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

function handleDomainsPanelToggle(isOpen) {
  domainsPanelOpen.value = isOpen;
}

function updateMode(nextMode) {
  emit('update:mode', nextMode);
}

function updateSearchType(nextType) {
  emit('update:searchType', nextType);
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
  width: min(var(--landing-hero-max-width, 720px), 100%);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  transition: transform 0.25s ease, gap 0.2s ease;
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

.landing-hero__content--domains-open {
  transform: translateY(-2.25rem);
  gap: 0.75rem;
}

.landing-hero-fade-enter-active,
.landing-hero-fade-leave-active {
  transition: opacity 0.18s ease, max-height 0.18s ease;
}

.landing-hero-fade-enter-from,
.landing-hero-fade-leave-to {
  opacity: 0;
  max-height: 0;
}

@media (max-width: 600px) {
  .landing-hero__content {
    padding: 0;
  }

  .landing-hero__content--domains-open {
    transform: translateY(-1.25rem);
  }
}
</style>
