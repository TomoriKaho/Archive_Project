<template>
  <div class="auth-shell">
    <div class="auth-panel">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1f2937, #3b82f6);
  padding: 24px;
}

.auth-panel {
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.25);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
}
</style>
