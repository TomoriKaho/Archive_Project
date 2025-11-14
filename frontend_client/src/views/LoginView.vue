<template>
  <div class="login-page">
    <button
      type="button"
      class="login-page__language"
      :aria-label="languageAriaLabel"
      @click="toggleLanguage"
    >
      <span class="login-page__language-flag" aria-hidden="true">{{ languageFlag }}</span>
      <span class="login-page__language-label">{{ languageLabel }}</span>
    </button>
    <div class="login-card">
      <h1 class="login-card__title">{{ texts.title }}</h1>
      <p class="login-card__subtitle">{{ texts.subtitle }}</p>
      <form class="login-form" @submit.prevent="handleSubmit">
        <label class="login-form__field">
          <span>{{ texts.emailLabel }}</span>
          <input v-model="email" type="email" required :placeholder="texts.emailPlaceholder" />
        </label>
        <label class="login-form__field">
          <span>{{ texts.passwordLabel }}</span>
          <input v-model="password" type="password" required :placeholder="texts.passwordPlaceholder" />
        </label>
        <p v-if="errorMessage" class="login-form__error">{{ errorMessage }}</p>
        <button class="login-form__submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? texts.submitting : texts.submit }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { usePreferencesStore } from '@/store/preferences';

const email = ref('');
const password = ref('');
const errorMessage = ref('');
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const preferencesStore = usePreferencesStore();

const isSubmitting = computed(() => authStore.status === 'loading');

const language = computed(() => preferencesStore.language);

const languagePack = {
  zh: {
    language: {
      label: '中文',
      flag: '🇨🇳',
      toggleAria: '切换到英文界面'
    },
    texts: {
      title: '登录 Archive AI',
      subtitle: '使用个人账号访问客户端对话体验。',
      emailLabel: '邮箱',
      emailPlaceholder: 'you@example.com',
      passwordLabel: '密码',
      passwordPlaceholder: '请输入密码',
      submit: '登录',
      submitting: '登录中…',
      errorFallback: '登录失败，请稍后重试。'
    }
  },
  en: {
    language: {
      label: 'English',
      flag: '🇺🇸',
      toggleAria: 'Switch to the Chinese interface'
    },
    texts: {
      title: 'Sign in to Archive AI',
      subtitle: 'Use your account to access the client chat experience.',
      emailLabel: 'Email',
      emailPlaceholder: 'you@example.com',
      passwordLabel: 'Password',
      passwordPlaceholder: 'Enter your password',
      submit: 'Sign in',
      submitting: 'Signing in…',
      errorFallback: 'Sign-in failed. Please try again later.'
    }
  }
};

const texts = computed(() => languagePack[language.value].texts);
const languageLabel = computed(() => languagePack[language.value].language.label);
const languageFlag = computed(() => languagePack[language.value].language.flag);
const languageAriaLabel = computed(() => languagePack[language.value].language.toggleAria);

watch(
  language,
  (value, oldValue) => {
    const locale = value === 'zh' ? 'zh-CN' : 'en-US';
    document.documentElement.setAttribute('lang', locale);
    if (oldValue && errorMessage.value === languagePack[oldValue].texts.errorFallback) {
      errorMessage.value = languagePack[value].texts.errorFallback;
    }
  },
  { immediate: true }
);

function toggleLanguage() {
  preferencesStore.toggleLanguage();
}

async function handleSubmit() {
  errorMessage.value = '';
  try {
    await authStore.login({ email: email.value, password: password.value });
    const redirect = route.query.redirect || '/';
    router.replace(redirect);
  } catch (error) {
    errorMessage.value =
      error.response?.data?.message || error.message || texts.value.errorFallback;
  }
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  background: linear-gradient(135deg, #dbe4ff, #f5f5ff);
  position: relative;
}

.login-page__language {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  border-radius: 18px;
  padding: 0.55rem 1.1rem;
  background: linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%);
  color: #1c2754;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 16px 40px rgba(28, 39, 84, 0.18);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.login-page__language:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 48px rgba(28, 39, 84, 0.24);
}

.login-page__language-flag {
  font-size: 1.1rem;
  line-height: 1;
}

.login-page__language-label {
  white-space: nowrap;
}

.login-card {
  width: min(420px, 100%);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  padding: 2.75rem 2.5rem;
  box-shadow: 0 30px 60px rgba(26, 43, 90, 0.16);
  backdrop-filter: blur(8px);
}

.login-card__title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #1f2a56;
}

.login-card__subtitle {
  margin: 0.75rem 0 2.5rem;
  color: #5a6b97;
  font-size: 0.95rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.login-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-weight: 600;
  color: #1f2a56;
}

.login-form__field input {
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  border: 1px solid #d0d9ff;
  font-size: 1rem;
  background: rgba(255, 255, 255, 0.85);
}

.login-form__field input:focus {
  outline: none;
  border-color: #7b5bff;
  box-shadow: 0 0 0 3px rgba(123, 91, 255, 0.2);
}

.login-form__error {
  margin: -0.5rem 0 0;
  color: #cf3c4f;
  font-size: 0.9rem;
}

.login-form__submit {
  border: none;
  border-radius: 999px;
  padding: 0.9rem;
  font-size: 1.05rem;
  font-weight: 600;
  background: linear-gradient(135deg, #4866ff, #7b5bff);
  color: #fff;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.login-form__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .login-page {
    padding: 1.5rem;
  }

  .login-page__language {
    top: 1rem;
    right: 1rem;
    padding: 0.5rem 0.95rem;
    font-size: 0.9rem;
  }

  .login-page__language-flag {
    font-size: 1rem;
  }
}
</style>
