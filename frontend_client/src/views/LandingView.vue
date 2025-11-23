<template>
  <div class="landing-view">
    <LandingHero
      v-model="query"
      :texts="heroTexts"
      :domains="domainOptions"
      :selected-domains="selectedDomains"
      :submitting="isCreatingConversation"
      @submit="handleSubmit"
      @update:domains="updateDomains"
    />
    <div class="landing-view__quick-actions">
      <button
        type="button"
        class="landing-view__fab landing-view__fab--history"
        :aria-label="heroTexts.history"
        @click="openHistory"
      >
        <span class="landing-view__fab-icon" aria-hidden="true">🕘</span>
        <span class="landing-view__fab-label">{{ heroTexts.history }}</span>
      </button>
      <button
        type="button"
        class="landing-view__fab landing-view__fab--language"
        :aria-label="languageAriaLabel"
        @click="toggleLanguage"
      >
        <span class="landing-view__fab-icon" aria-hidden="true">{{ languageFlag }}</span>
        <span class="landing-view__fab-label">{{ languageLabel }}</span>
      </button>
      <button
        type="button"
        class="landing-view__fab landing-view__fab--logout"
        :aria-label="heroTexts.logoutAria"
        @click="handleLogout"
      >
        <span class="landing-view__fab-icon" aria-hidden="true">⏻</span>
        <span class="landing-view__fab-label">{{ heroTexts.logout }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import LandingHero from '@/components/LandingHero.vue';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/auth';
import { useDomainsStore } from '@/store/domains';
import { usePreferencesStore } from '@/store/preferences';

const router = useRouter();
const chatStore = useChatStore();
const authStore = useAuthStore();
const domainsStore = useDomainsStore();
const preferencesStore = usePreferencesStore();

const query = ref('');
const isCreatingConversation = ref(false);

const language = computed(() => preferencesStore.language);
const selectedDomains = computed(() => preferencesStore.preferredDomainIds);
const domainOptions = computed(() => domainsStore.items);

const languagePack = {
  zh: {
    label: '中文',
    flag: '🇨🇳',
    toggleAria: '切换到英文界面',
    hero: {
      title: '太平洋丝绸之路・档案库智能助手',
      history: '查看历史会话',
      logout: '退出登录',
      logoutAria: '退出当前账号',
      composer: {
        placeholder: '在这里快速检索知识并与智能助手对话',
        submit: '开始对话',
        submitting: '创建中…',
        domainButton: '选择知识域',
        domainBadge: (count) => `已选${count}`,
        domainHint: '选择后发送消息时仅检索勾选的知识域，不勾选默认从全部知识域检索。',
        domainApply: '应用',
        domainClear: '清除'
      }
    }
  },
  en: {
    label: 'English',
    flag: '🇺🇸',
    toggleAria: 'Switch to Chinese interface',
    hero: {
      title: 'Pacific Silk Road · AI Assistant',
      subtitle: '',
      history: 'View Conversation History',
      logout: 'Log out',
      logoutAria: 'Log out of the current account',
      composer: {
        placeholder: 'Quickly search archival knowledge and chat with the assistant here.',
        submit: 'Start Chatting',
        submitting: 'Creating…',
        domainButton: 'Choose Domains',
        domainBadge: (count) => `${count} selected`,
        domainHint:
          'When selected, messages will only search the checked domains. Leave unchecked to search all domains.',
        domainApply: 'Apply',
        domainClear: 'Clear'
      }
    }
  }
};

const heroTexts = computed(() => languagePack[language.value].hero);
const languageLabel = computed(() => languagePack[language.value].label);
const languageFlag = computed(() => languagePack[language.value].flag);
const languageAriaLabel = computed(() => languagePack[language.value].toggleAria);

watch(
  language,
  (value) => {
    const locale = value === 'zh' ? 'zh-CN' : 'en-US';
    document.documentElement.setAttribute('lang', locale);
  },
  { immediate: true }
);

onMounted(() => {
  domainsStore.loadDomains({ force: false }).catch((error) => {
    console.error('加载领域失败', error);
  });
});

function toggleLanguage() {
  preferencesStore.toggleLanguage();
}

async function handleSubmit(value) {
  const content = value.trim();
  if (!content || isCreatingConversation.value) {
    return;
  }
  isCreatingConversation.value = true;
  try {
    const conversationId = await chatStore.createConversation({
      title: content.slice(0, 30),
      initialMessage: content,
      domainIds: selectedDomains.value
    });
    preferencesStore.setPreferredDomainIds([]);
    query.value = '';
    router.push({ name: 'chat', params: { conversationId } });
  } catch (error) {
    console.error('创建会话失败', error);
  } finally {
    isCreatingConversation.value = false;
  }
}

function openHistory() {
  router.push({ name: 'chat' });
}

function updateDomains(domainIds) {
  preferencesStore.setPreferredDomainIds(domainIds);
}

function handleLogout() {
  authStore.logout();
}
</script>

<style scoped lang="scss">
.landing-view {
  position: relative;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem 1.5rem 5rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05)),
    url('@/assets/pacific-map.png');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  isolation: isolate;
}

.landing-view__quick-actions {
  position: fixed;
  top: 1.5rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  z-index: 20;
}

.landing-view__fab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  border-radius: 18px;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 16px 40px rgba(28, 39, 84, 0.18);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.landing-view__fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 48px rgba(28, 39, 84, 0.24);
}

.landing-view__fab--language {
  background: linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%);
  color: #1c2754;
}

.landing-view__fab--history {
  background: linear-gradient(135deg, #e3f4ff 0%, #bde5ff 100%);
  color: #1f8fe5;
}

.landing-view__fab--logout {
  background: linear-gradient(135deg, #ff6b6b, #ff8e53);
  color: #fff;
}

.landing-view__fab-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.landing-view__fab-label {
  white-space: nowrap;
}

@media (max-width: 768px) {
  .landing-view__quick-actions {
    right: 1.25rem;
    top: 1rem;
  }

  .landing-view__fab {
    padding: 0.55rem 1rem;
    font-size: 0.9rem;
  }

  .landing-view__fab-icon {
    font-size: 1rem;
  }
}
</style>
