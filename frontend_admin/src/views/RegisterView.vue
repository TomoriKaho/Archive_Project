<template>
  <form class="auth-form" @submit.prevent="onSubmit">
    <h2 class="auth-form__title">{{ t('auth.register.title') }}</h2>
    <p class="auth-form__subtitle">
      {{ t('auth.register.subtitle') }}
    </p>

    <div class="form-field" :class="{ 'form-field--error': errors.name }">
      <label for="name">{{ t('auth.register.nameLabel') }}</label>
      <input
        id="name"
        v-model.trim="form.name"
        type="text"
        :placeholder="t('auth.register.namePlaceholder')"
      />
      <p v-if="errors.name" class="form-field__error">{{ errors.name }}</p>
    </div>

    <div class="form-field" :class="{ 'form-field--error': errors.email }">
      <label for="email">{{ t('auth.register.emailLabel') }}</label>
      <input
        id="email"
        v-model.trim="form.email"
        type="email"
        :placeholder="t('auth.register.emailPlaceholder')"
      />
      <p v-if="errors.email" class="form-field__error">{{ errors.email }}</p>
    </div>

    <div class="form-field" :class="{ 'form-field--error': errors.password }">
      <label for="password">{{ t('auth.register.passwordLabel') }}</label>
      <input
        id="password"
        v-model="form.password"
        type="password"
        :placeholder="t('auth.register.passwordPlaceholder')"
      />
      <p v-if="errors.password" class="form-field__error">
        {{ errors.password }}
      </p>
    </div>

    <div
      class="form-field"
      :class="{ 'form-field--error': errors.confirmPassword }"
    >
      <label for="confirmPassword">{{ t('auth.register.confirmLabel') }}</label>
      <input
        id="confirmPassword"
        v-model="form.confirmPassword"
        type="password"
        :placeholder="t('auth.register.confirmPlaceholder')"
      />
      <p v-if="errors.confirmPassword" class="form-field__error">
        {{ errors.confirmPassword }}
      </p>
    </div>

    <button
      class="button button--primary"
      type="submit"
      :disabled="isSubmitting"
    >
      {{
        isSubmitting
          ? t('auth.register.submitting')
          : t('auth.register.submit')
      }}
    </button>

    <p class="auth-form__footer">
      {{ t('auth.register.haveAccount') }}
      <RouterLink :to="{ name: 'login' }">{{ t('auth.register.loginLink') }}</RouterLink>
    </p>
  </form>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useI18n } from 'vue-i18n';

import { useAuthStore } from '@/store/auth';

const authStore = useAuthStore();
const { t } = useI18n();

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

const isSubmitting = ref(false);

function validate() {
  const trimmedName = form.name.trim();
  if (!trimmedName) {
    errors.name = t('auth.register.validation.nameRequired');
  } else if (trimmedName.length > 30) {
    errors.name = t('auth.register.validation.nameTooLong');
  } else {
    errors.name = '';
  }

  const emailRegex = /[^\s@]+@[^\s@]+\.[^\s@]+/;
  if (!form.email) {
    errors.email = t('auth.register.validation.emailRequired');
  } else if (!emailRegex.test(form.email)) {
    errors.email = t('auth.register.validation.emailInvalid');
  } else {
    errors.email = '';
  }

  if (!form.password) {
    errors.password = t('auth.register.validation.passwordRequired');
  } else if (
    form.password.length < 8 ||
    !/[A-Z]/.test(form.password) ||
    !/\d/.test(form.password)
  ) {
    errors.password = t('auth.register.validation.passwordWeak');
  } else {
    errors.password = '';
  }

  if (form.confirmPassword !== form.password) {
    errors.confirmPassword = t('auth.register.validation.passwordMismatch');
  } else {
    errors.confirmPassword = '';
  }

  return (
    !errors.name && !errors.email && !errors.password && !errors.confirmPassword
  );
}

async function onSubmit() {
  if (!validate()) return;
  isSubmitting.value = true;
  try {
    const trimmedName = form.name.trim();
    await authStore.register({
      full_name: trimmedName,
      email: form.email,
      password: form.password
    });
  } catch (error) {
    // toast handled in store
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.auth-form__title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.auth-form__subtitle {
  margin: -8px 0 16px;
  color: #6b7280;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field label {
  font-weight: 600;
}

.form-field input,
.form-field textarea,
.form-field select {
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
}

.form-field--error input {
  border-color: #ef4444;
}

.form-field__error {
  color: #ef4444;
  font-size: 13px;
}

.button {
  border: none;
  border-radius: 8px;
  padding: 12px 18px;
  font-weight: 600;
  cursor: pointer;
  font-size: 15px;
}

.button--primary {
  background: #1f2937;
  color: #ffffff;
}

.button[disabled] {
  opacity: 0.7;
  cursor: not-allowed;
}

.auth-form__footer {
  text-align: center;
  color: #6b7280;
}
</style>
