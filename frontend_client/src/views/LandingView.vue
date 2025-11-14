<template>
  <div class="landing-view">
    <LandingHero v-model="query" @submit="handleSubmit" @show-history="openHistory" />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import LandingHero from '@/components/LandingHero.vue';
import { useChatStore } from '@/store/chat';

const router = useRouter();
const chatStore = useChatStore();
const query = ref('');

async function handleSubmit(value) {
  const content = value.trim();
  if (!content) {
    return;
  }
  try {
    const conversationId = await chatStore.createConversation({
      title: content.slice(0, 30),
      initialMessage: content
    });
    router.push({ name: 'chat', params: { conversationId } });
  } catch (error) {
    console.error('创建会话失败', error);
  }
}

function openHistory() {
  router.push({ name: 'chat' });
}
</script>

<style scoped>
.landing-view {
  min-height: 100vh;
  background: transparent;
}
</style>
