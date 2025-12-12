<template>
  <div class="landing-view">
    <LandingHero
      v-model="query"
      :texts="heroTexts"
      :domains="domainOptions"
      :selected-domains="selectedDomains"
      :submitting="isCreatingConversation"
      :mode="searchMode"
      :search-type="searchType"
      :lifted="isTraditionalMode"
      @submit="handleSubmit"
      @update:domains="updateDomains"
      @update:mode="setSearchMode"
      @update:searchType="setSearchType"
    />
    <div v-if="isTraditionalMode" class="landing-view__archives">
      <ArchiveResultsTable
        :archives="archives"
        :page="searchPage"
        :page-size="pageSize"
        :total="totalArchives"
        :state="searchState"
        :error-message="searchError"
        :texts="archiveTableTexts"
        @update:page="loadPage"
      />
    </div>
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
import ArchiveResultsTable from '@/components/ArchiveResultsTable.vue';
import LandingHero from '@/components/LandingHero.vue';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/auth';
import { useDomainsStore } from '@/store/domains';
import { usePreferencesStore } from '@/store/preferences';
import { searchArchives } from '@/services/search';

const router = useRouter();
const chatStore = useChatStore();
const authStore = useAuthStore();
const domainsStore = useDomainsStore();
const preferencesStore = usePreferencesStore();

const query = ref('');
const isCreatingConversation = ref(false);
const searchMode = ref('assistant');
const searchType = ref('precise');
const searchState = ref('idle');
const searchError = ref('');
const archives = ref([]);
const totalArchives = ref(0);
const searchPage = ref(1);
const pageSize = 10;

const language = computed(() => preferencesStore.language);
const selectedDomains = computed(() => preferencesStore.preferredDomainIds);
const domainOptions = computed(() => domainsStore.items);
const isTraditionalMode = computed(() => searchMode.value === 'traditional');

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
        traditionalPlaceholder: '在这里搜索档案内容',
        submit: '开始对话',
        traditionalSubmit: '开始搜索',
        submitting: '创建中…',
        domainButton: '选择知识域',
        domainBadge: (count) => `已选${count}`,
        domainHint: '选择后仅检索勾选的知识域，                不勾选默认从全部知识域检索。',
        domainApply: '应用',
        domainClear: '清除',
        switchToTraditional: '切换至传统搜索',
        switchToAssistant: '切换至智能助手',
        precise: '精准搜索',
        fuzzy: '模糊搜索'
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
        traditionalPlaceholder: 'Search archive contents here.',
        submit: 'Start Chatting',
        traditionalSubmit: 'Start Searching',
        submitting: 'Creating…',
        domainButton: 'Choose Domains',
        domainBadge: (count) => `${count} selected`,
        domainHint:
          'When selected, messages will only search the checked domains. Leave unchecked to search all domains.',
        domainApply: 'Apply',
        domainClear: 'Clear',
        switchToTraditional: 'Switch to Traditional Search',
        switchToAssistant: 'Switch to AI Assistant',
        precise: 'Precise Search',
        fuzzy: 'Fuzzy Search'
      }
    }
  }
};

const heroTexts = computed(() => {
  const base = languagePack[language.value].hero;
  return {
    ...base,
    composer: {
      ...base.composer,
      placeholder:
        searchMode.value === 'traditional'
          ? base.composer.traditionalPlaceholder
          : base.composer.placeholder
    }
  };
});
const archiveTableTexts = computed(() =>
  language.value === 'zh'
    ? {
        placeholder: '搜索结果在这里显示',
        loading: '正在加载…',
        error: '搜索失败，请稍后重试',
        empty: '未找到符合条件的档案',
        collapse: '收起',
        expand: '展开',
        previous: '上一页',
        next: '下一页',
        columns: {
          index: '页序号',
          archive: '档案名称',
          document: '文档名称',
          domain: '知识域名称',
          detail: '详细信息'
        }
      }
    : {
        placeholder: 'Search results will appear here',
        loading: 'Loading…',
        error: 'Search failed. Please try again later.',
        empty: 'No archives found',
        collapse: 'Collapse',
        expand: 'Expand',
        previous: 'Previous',
        next: 'Next',
        columns: {
          index: 'Page',
          archive: 'Archive Name',
          document: 'Document Name',
          domain: 'Domain',
          detail: 'Details'
        }
      }
);
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
  if (isTraditionalMode.value) {
    performArchiveSearch(1, content);
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

function setSearchMode(mode) {
  const normalized = mode === 'traditional' ? 'traditional' : 'assistant';
  searchMode.value = normalized;
  if (normalized === 'assistant') {
    searchState.value = 'idle';
    searchError.value = '';
    archives.value = [];
    totalArchives.value = 0;
    searchPage.value = 1;
  }
}

function setSearchType(type) {
  const normalized = type === 'fuzzy' ? 'fuzzy' : 'precise';
  searchType.value = normalized;
  if (isTraditionalMode.value && query.value.trim()) {
    performArchiveSearch(1);
  }
}

async function performArchiveSearch(page = 1, content = query.value.trim()) {
  const keyword = content.trim();
  if (!keyword) {
    searchState.value = 'idle';
    archives.value = [];
    totalArchives.value = 0;
    return;
  }
  searchState.value = 'loading';
  searchError.value = '';
  try {
    const response = await searchArchives({
      query: keyword,
      domainIds: selectedDomains.value,
      mode: searchType.value,
      page,
      pageSize
    });
    archives.value = response?.items || response?.results || [];
    totalArchives.value = Number(response?.total) || archives.value.length;
    searchPage.value = page;
    searchState.value = 'ready';
  } catch (error) {
    console.error('搜索档案失败', error);
    searchState.value = 'error';
    searchError.value = error?.response?.data?.detail || error.message || '';
  }
}

function loadPage(page) {
  const target = Math.max(1, page);
  performArchiveSearch(target);
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
  flex-direction: column;
  align-items: center;
  padding: 7rem 1.5rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05)),
    url('@/assets/pacific-map2.png');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  isolation: isolate;
  --landing-hero-max-width: 820px;
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
  background: linear-gradient(135deg, #90c8ed 0%, #59b6f4 100%);
  color: #103a5a;
}

.landing-view__fab--logout {
  background: linear-gradient(135deg, #f03e3e, #fc742a);
  color: #fff;
}

.landing-view__fab-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.landing-view__fab-label {
  white-space: nowrap;
}

.landing-view__archives {
  width: min(var(--landing-hero-max-width, 720px), 100%);
  margin: 1rem auto 0;
  height: clamp(520px, 72vh, calc(100vh - 160px));
  overflow: auto;
  padding: 0 0.5rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.landing-view__archives::-webkit-scrollbar {
  width: 8px;
}

.landing-view__archives::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.2);
  border-radius: 999px;
}

.landing-view__archives::-webkit-scrollbar-track {
  background: transparent;
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
