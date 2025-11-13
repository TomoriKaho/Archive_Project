<template>
  <div id="app" class="app-shell">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
};
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}
</style>
