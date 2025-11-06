<template>
  <form class="auth-form" @submit.prevent="onSubmit">
    <h2 class="auth-form__title">Welcome back</h2>
    <p class="auth-form__subtitle">
      Sign in to continue managing your archives.
    </p>

    <div class="form-field" :class="{ 'form-field--error': errors.email }">
      <label for="email">Email</label>
      <input
        id="email"
        v-model.trim="form.email"
        type="email"
        placeholder="you@example.com"
      />
      <p v-if="errors.email" class="form-field__error">{{ errors.email }}</p>
    </div>

    <div class="form-field" :class="{ 'form-field--error': errors.password }">
      <label for="password">Password</label>
      <input
        id="password"
        v-model="form.password"
        type="password"
        placeholder="••••••••"
      />
      <p v-if="errors.password" class="form-field__error">
        {{ errors.password }}
      </p>
    </div>

    <button
      class="button button--primary"
      type="submit"
      :disabled="isSubmitting"
    >
      {{ isSubmitting ? 'Signing in…' : 'Sign In' }}
    </button>

    <p class="auth-form__footer">
      Need an account?
      <RouterLink :to="{ name: 'register' }">Register</RouterLink>
    </p>
  </form>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter, RouterLink } from 'vue-router';

import { useAuthStore } from '@/store/auth';

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  email: '',
  password: ''
});

const errors = reactive({
  email: '',
  password: ''
});

const isSubmitting = ref(false);

function validate() {
  errors.email = '';
  errors.password = '';

  const emailRegex = /[^\s@]+@[^\s@]+\.[^\s@]+/;
  if (!form.email) {
    errors.email = 'Email is required.';
  } else if (!emailRegex.test(form.email)) {
    errors.email = 'Enter a valid email address.';
  }

  if (!form.password) {
    errors.password = 'Password is required.';
  } else if (
    form.password.length < 8 ||
    !/[A-Z]/.test(form.password) ||
    !/\d/.test(form.password)
  ) {
    errors.password =
      'Use at least 8 characters with a number and uppercase letter.';
  }

  return !errors.email && !errors.password;
}

async function onSubmit() {
  if (!validate()) return;
  isSubmitting.value = true;
  try {
    await authStore.login({ ...form });
    const redirect = router.currentRoute.value.query.redirect || {
      name: 'dashboard'
    };
    router.push(redirect);
  } catch (error) {
    // error already handled by store toasts
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
