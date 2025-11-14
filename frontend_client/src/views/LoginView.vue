<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-card__title">登录 Archive AI</h1>
      <p class="login-card__subtitle">使用个人账号访问客户端对话体验。</p>
      <form class="login-form" @submit.prevent="handleSubmit">
        <label class="login-form__field">
          <span>邮箱</span>
          <input v-model="email" type="email" required placeholder="you@example.com" />
        </label>
        <label class="login-form__field">
          <span>密码</span>
          <input v-model="password" type="password" required placeholder="请输入密码" />
        </label>
        <p v-if="errorMessage" class="login-form__error">{{ errorMessage }}</p>
        <button class="login-form__submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? '登录中…' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';

const email = ref('');
const password = ref('');
const errorMessage = ref('');
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const isSubmitting = computed(() => authStore.status === 'loading');

async function handleSubmit() {
  errorMessage.value = '';
  try {
    await authStore.login({ email: email.value, password: password.value });
    const redirect = route.query.redirect || '/';
    router.replace(redirect);
  } catch (error) {
    errorMessage.value =
      error.response?.data?.message || error.message || '登录失败，请稍后重试。';
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
</style>
