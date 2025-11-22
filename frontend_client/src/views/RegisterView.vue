<template>
  <div class="register-page">
    <button
      type="button"
      class="register-page__language"
      :aria-label="languageAriaLabel"
      @click="toggleLanguage"
    >
      <span class="register-page__language-flag" aria-hidden="true">{{ languageFlag }}</span>
      <span class="register-page__language-label">{{ languageLabel }}</span>
    </button>
    <div class="register-card">
      <h1 class="register-card__title">{{ texts.title }}</h1>
      <p class="register-card__subtitle">{{ texts.subtitle }}</p>
      <form class="register-form" @submit.prevent="handleSubmit">
        <label class="register-form__field">
          <span>{{ texts.nameLabel }}</span>
          <input v-model="form.name" type="text" :placeholder="texts.namePlaceholder" />
          <small v-if="errors.name" class="register-form__error">{{ errors.name }}</small>
        </label>
        <label class="register-form__field">
          <span>{{ texts.emailLabel }}</span>
          <input v-model="form.email" type="email" :placeholder="texts.emailPlaceholder" />
          <small v-if="errors.email" class="register-form__error">{{ errors.email }}</small>
        </label>
        <label class="register-form__field">
          <span>{{ texts.passwordLabel }}</span>
          <input
            v-model="form.password"
            type="password"
            :placeholder="texts.passwordPlaceholder"
          />
          <small v-if="errors.password" class="register-form__error">{{ errors.password }}</small>
        </label>
        <label class="register-form__field">
          <span>{{ texts.confirmLabel }}</span>
          <input
            v-model="form.confirmPassword"
            type="password"
            :placeholder="texts.confirmPlaceholder"
          />
          <small v-if="errors.confirmPassword" class="register-form__error">
            {{ errors.confirmPassword }}
          </small>
        </label>
        <p v-if="submitError" class="register-form__submit-error">{{ submitError }}</p>
        <button class="register-form__submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? texts.submitting : texts.submit }}
        </button>
        <p class="register-form__hint">
          {{ texts.haveAccount }}
          <RouterLink class="register-form__link" :to="{ name: 'login' }">{{ texts.loginLink }}</RouterLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { usePreferencesStore } from '@/store/preferences';

const form = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const errors = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const submitError = ref('');

const authStore = useAuthStore();
const router = useRouter();
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
      title: '创建账号',
      subtitle: '注册后即可登录并开始聊天。',
      nameLabel: '姓名',
      namePlaceholder: '请输入姓名',
      emailLabel: '邮箱',
      emailPlaceholder: 'you@example.com',
      passwordLabel: '密码',
      passwordPlaceholder: '至少8位，需包含字母和数字',
      confirmLabel: '确认密码',
      confirmPlaceholder: '再次输入密码',
      submit: '注册',
      submitting: '注册中…',
      errorFallback: '注册失败，请稍后重试。',
      emailTaken: '邮箱已被使用，请直接登录或更换邮箱。',
      haveAccount: '已经有账号了？',
      loginLink: '去登录',
      validation: {
        nameRequired: '请输入姓名。',
        nameTooLong: '姓名长度需在 30 字以内。',
        emailRequired: '请输入邮箱。',
        emailInvalid: '请输入有效的邮箱地址。',
        passwordRequired: '请输入密码。',
        passwordWeak: '密码至少 8 位，需包含字母和数字。',
        passwordMismatch: '两次输入的密码不一致。'
      }
    }
  },
  en: {
    language: {
      label: 'English',
      flag: '🇺🇸',
      toggleAria: 'Switch to the Chinese interface'
    },
    texts: {
      title: 'Create your account',
      subtitle: 'Register to sign in and start chatting.',
      nameLabel: 'Name',
      namePlaceholder: 'Your name',
      emailLabel: 'Email',
      emailPlaceholder: 'you@example.com',
      passwordLabel: 'Password',
      passwordPlaceholder: 'At least 8 characters with letters and numbers',
      confirmLabel: 'Confirm password',
      confirmPlaceholder: 'Re-enter your password',
      submit: 'Create account',
      submitting: 'Creating…',
      errorFallback: 'Registration failed. Please try again later.',
      emailTaken: 'Email is already registered. Please sign in or use another email.',
      haveAccount: 'Already have an account?',
      loginLink: 'Sign in',
      validation: {
        nameRequired: 'Please enter your name.',
        nameTooLong: 'Name must be 30 characters or fewer.',
        emailRequired: 'Please enter your email address.',
        emailInvalid: 'Please enter a valid email address.',
        passwordRequired: 'Please enter a password.',
        passwordWeak: 'Password must be at least 8 characters with letters and numbers.',
        passwordMismatch: 'Passwords do not match.'
      }
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
    if (oldValue && submitError.value === languagePack[oldValue].texts.errorFallback) {
      submitError.value = languagePack[value].texts.errorFallback;
    }
  },
  { immediate: true }
);

function toggleLanguage() {
  preferencesStore.toggleLanguage();
}

function validate() {
  const emailRegex = /[^\s@]+@[^\s@]+\.[^\s@]+/;
  const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

  const trimmedName = form.name.trim();
  if (!trimmedName) {
    errors.name = texts.value.validation.nameRequired;
  } else if (trimmedName.length > 30) {
    errors.name = texts.value.validation.nameTooLong;
  } else {
    errors.name = '';
  }

  const trimmedEmail = form.email.trim();
  if (!trimmedEmail) {
    errors.email = texts.value.validation.emailRequired;
  } else if (!emailRegex.test(trimmedEmail)) {
    errors.email = texts.value.validation.emailInvalid;
  } else {
    errors.email = '';
  }

  if (!form.password) {
    errors.password = texts.value.validation.passwordRequired;
  } else if (!passwordRegex.test(form.password)) {
    errors.password = texts.value.validation.passwordWeak;
  } else {
    errors.password = '';
  }

  if (form.confirmPassword !== form.password) {
    errors.confirmPassword = texts.value.validation.passwordMismatch;
  } else {
    errors.confirmPassword = '';
  }

  return !errors.name && !errors.email && !errors.password && !errors.confirmPassword;
}

async function handleSubmit() {
  submitError.value = '';
  if (!validate()) {
    return;
  }

  try {
    const trimmedName = form.name.trim();
    await authStore.register({
      full_name: trimmedName,
      email: form.email.trim(),
      password: form.password
    });
    router.replace({ name: 'login', query: { registered: '1' } });
  } catch (error) {
    const status = error.response?.status;
    if (status === 409) {
      submitError.value = error.response?.data?.message || texts.value.emailTaken;
    } else {
      submitError.value = error.response?.data?.message || texts.value.errorFallback;
    }
  }
}
</script>

<style scoped lang="scss">
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  position: relative;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05)),
    url('@/assets/pacific-map.png');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
}

.register-page__language {
  position: absolute;
  right: 1.5rem;
  bottom: 1.5rem;
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
  z-index: 1;
}

.register-page__language:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 48px rgba(28, 39, 84, 0.24);
}

.register-page__language-flag {
  font-size: 1.1rem;
  line-height: 1;
}

.register-page__language-label {
  white-space: nowrap;
}

.register-card {
  width: min(480px, 100%);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  padding: 2.75rem 2.5rem;
  box-shadow: 0 30px 60px rgba(26, 43, 90, 0.16);
  backdrop-filter: blur(8px);
  position: relative;
  z-index: 1;
}

.register-card__title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #1f2a56;
}

.register-card__subtitle {
  margin: 0.75rem 0 2.5rem;
  color: #5a6b97;
  font-size: 0.95rem;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.register-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-weight: 600;
  color: #1f2a56;
}

.register-form__field input {
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  border: 1px solid #d0d9ff;
  font-size: 1rem;
  background: rgba(255, 255, 255, 0.85);
}

.register-form__field input:focus {
  outline: none;
  border-color: #7b5bff;
  box-shadow: 0 0 0 3px rgba(123, 91, 255, 0.2);
}

.register-form__error {
  margin: -0.35rem 0 0;
  color: #cf3c4f;
  font-size: 0.9rem;
  font-weight: 500;
}

.register-form__submit-error {
  margin: -0.5rem 0 0;
  color: #cf3c4f;
  font-size: 0.95rem;
  font-weight: 600;
}

.register-form__submit {
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

.register-form__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-form__hint {
  margin: 0.5rem 0 0;
  text-align: center;
  color: #4a5b87;
  font-weight: 600;
}

.register-form__link {
  color: #4866ff;
  text-decoration: none;
  margin-left: 0.35rem;
}

.register-form__link:hover {
  text-decoration: underline;
}

@media (max-width: 640px) {
  .register-page {
    padding: 1.5rem;
  }

  .register-page__language {
    right: 1rem;
    bottom: 1rem;
    padding: 0.5rem 0.95rem;
    font-size: 0.9rem;
  }

  .register-page__language-flag {
    font-size: 1rem;
  }
}
</style>
