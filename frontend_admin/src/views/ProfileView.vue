<template>
  <section class="profile">
    <header class="profile__header">
      <div>
        <h2>{{ t('profile.title') }}</h2>
        <p>{{ t('profile.subtitle') }}</p>
      </div>
    </header>

    <form class="profile__form" @submit.prevent="saveProfile">
      <div class="form-field" :class="{ 'form-field--error': errors.full_name }">
        <label for="profile-name">{{ t('profile.form.nameLabel') }}</label>
        <input
          id="profile-name"
          v-model.trim="form.full_name"
          type="text"
          :placeholder="t('profile.form.namePlaceholder')"
        />
        <p v-if="errors.full_name" class="form-field__error">{{ errors.full_name }}</p>
      </div>

      <div class="form-field" :class="{ 'form-field--error': errors.email }">
        <label for="profile-email">{{ t('profile.form.emailLabel') }}</label>
        <input
          id="profile-email"
          v-model.trim="form.email"
          type="email"
          :placeholder="t('profile.form.emailPlaceholder')"
          required
        />
        <p v-if="errors.email" class="form-field__error">{{ errors.email }}</p>
      </div>

      <div class="form-field" :class="{ 'form-field--error': errors.password }">
        <label for="profile-password">{{ t('profile.form.passwordLabel') }}</label>
        <input
          id="profile-password"
          v-model.trim="form.password"
          type="password"
          :placeholder="t('profile.form.passwordPlaceholder')"
        />
        <p class="form-field__hint">{{ t('profile.form.passwordHint') }}</p>
        <p v-if="errors.password" class="form-field__error">{{ errors.password }}</p>
      </div>

      <div class="form-field" :class="{ 'form-field--error': errors.confirmPassword }">
        <label for="profile-confirm">{{ t('profile.form.confirmLabel') }}</label>
        <input
          id="profile-confirm"
          v-model.trim="form.confirmPassword"
          type="password"
          :placeholder="t('profile.form.confirmPlaceholder')"
        />
        <p v-if="errors.confirmPassword" class="form-field__error">
          {{ errors.confirmPassword }}
        </p>
      </div>

      <div class="profile__actions">
        <button class="button button--primary" type="submit" :disabled="isSaving">
          {{ isSaving ? t('profile.form.saving') : t('profile.form.save') }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { useAuthStore } from '@/store/auth';
import { useUiStore } from '@/store/ui';
import { updateUser } from '@/services/users';

const { t } = useI18n();
const authStore = useAuthStore();
const uiStore = useUiStore();

const user = computed(() => authStore.user);

const form = reactive({
  full_name: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const errors = reactive({
  full_name: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const isSaving = ref(false);

function populateForm() {
  if (!user.value) return;
  form.full_name = user.value.full_name || '';
  form.email = user.value.email || '';
  form.password = '';
  form.confirmPassword = '';
  clearErrors();
}

function clearErrors() {
  errors.full_name = '';
  errors.email = '';
  errors.password = '';
  errors.confirmPassword = '';
}

function validate() {
  clearErrors();
  let valid = true;
  if (!form.email) {
    errors.email = t('profile.validation.emailRequired');
    valid = false;
  } else if (!/^\S+@\S+\.\S+$/.test(form.email)) {
    errors.email = t('profile.validation.emailInvalid');
    valid = false;
  }

  if (form.password) {
    if (form.password.length < 8) {
      errors.password = t('profile.validation.passwordLength');
      valid = false;
    }
    if (form.password !== form.confirmPassword) {
      errors.confirmPassword = t('profile.validation.passwordMismatch');
      valid = false;
    }
  } else if (form.confirmPassword) {
    errors.confirmPassword = t('profile.validation.passwordMismatch');
    valid = false;
  }

  return valid;
}

async function saveProfile() {
  if (!user.value) {
    return;
  }
  if (!validate()) {
    return;
  }

  isSaving.value = true;
  try {
    const payload = {
      full_name: (form.full_name || '').trim(),
      email: form.email.trim().toLowerCase()
    };
    const trimmedPassword = form.password.trim();
    if (trimmedPassword) {
      payload.password = trimmedPassword;
    }

    await updateUser(user.value.id, payload);
    await authStore.refreshUser();
    populateForm();
    uiStore.showToast({
      type: 'success',
      message: t('profile.toast.updateSuccess')
    });
  } catch (error) {
    uiStore.showToast({
      type: 'error',
      message:
        error.response?.data?.detail ||
        error.response?.data?.message ||
        t('profile.toast.updateError')
    });
  } finally {
    isSaving.value = false;
  }
}

onMounted(async () => {
  if (!authStore.initialized) {
    try {
      await authStore.initialize();
    } catch (error) {
      // initialization errors handled by auth store toasts
    }
  }
  populateForm();
});

watch(user, populateForm);
</script>

<style scoped>
.profile__header h2 {
  margin: 0;
  font-size: 28px;
  color: #111827;
}

.profile__header p {
  margin: 8px 0 24px;
  color: #6b7280;
}

.profile__form {
  display: grid;
  gap: 24px;
  max-width: 480px;
}

.profile__actions {
  display: flex;
  gap: 12px;
}
</style>
