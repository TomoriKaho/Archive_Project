<template>
  <div
    class="landing-view"
    :class="{ 'landing-view--traditional': isTraditionalMode, 'landing-view--ready': isUiReady }"
  >
    <div class="landing-view__content">
      <div class="landing-view__hero">
        <!-- Search bar fades when switching modes (and on first render). -->
        <Transition name="landing-hero" mode="out-in" appear>
          <LandingHero
            :key="heroAnimKey"
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
        </Transition>
      </div>

      <!-- Results area fades in when entering traditional search mode. -->
      <Transition name="landing-archives" appear>
        <div v-if="isTraditionalMode" class="landing-view__archives">
          <div class="landing-view__archives-panel">
            <!-- Centered placeholder for the idle state. -->
            <div v-if="searchState === 'idle'" class="landing-view__archives-placeholder">
              {{ archiveTableTexts.placeholder }}
            </div>

            <ArchiveResultsTable
              v-else
              class="landing-view__archives-table"
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
        </div>
      </Transition>
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
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

// UI animation helpers
const isUiReady = ref(false);
const heroAnimKey = ref(0);
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
        switchToFuzzy: '切换至模糊搜索',
        switchToPrecise: '切换至精准搜索',
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
        switchToFuzzy: 'Switch to fuzzy search',
        switchToPrecise: 'Switch to precise search',
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

// Re-run the hero fade animation whenever the mode changes.
watch(searchMode, () => {
  heroAnimKey.value += 1;
});

let previousHtmlOverflow = '';
let previousBodyOverflow = '';
let previousHtmlHeight = '';
let previousBodyHeight = '';

onMounted(() => {
  // Keep the landing page locked to a single viewport (no page-level scrolling).
  // Note: we restore the previous values when leaving this view.
  previousHtmlOverflow = document.documentElement.style.overflow;
  previousBodyOverflow = document.body.style.overflow;
  previousHtmlHeight = document.documentElement.style.height;
  previousBodyHeight = document.body.style.height;

  document.documentElement.style.overflow = 'hidden';
  document.body.style.overflow = 'hidden';
  document.documentElement.style.height = '100%';
  document.body.style.height = '100%';

  // Allow CSS transitions to run after the first paint.
  requestAnimationFrame(() => {
    isUiReady.value = true;
  });

  domainsStore.loadDomains({ force: false }).catch((error) => {
    console.error('加载领域失败', error);
  });
});

onUnmounted(() => {
  document.documentElement.style.overflow = previousHtmlOverflow;
  document.body.style.overflow = previousBodyOverflow;
  document.documentElement.style.height = previousHtmlHeight;
  document.body.style.height = previousBodyHeight;
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
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6rem 1.5rem 1.75rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05)),
    url('@/assets/pacific-map2.png');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  isolation: isolate;
  /* Shared width for search + results (animated when mode changes). */
  --landing-content-max-width: 800px;
  overflow: hidden;
}

.landing-view--traditional {
  --landing-content-max-width: 1200px;
}

/*
  One shared width container for both the search box and the results panel.
  Animating a single element is noticeably smoother than animating both panels
  (especially when the results area is large).
*/
.landing-view__content {
  width: 100%;
  max-width: var(--landing-content-max-width);
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

.landing-view__hero {
  width: 100%;
  margin: 0 0 1.1rem;
  flex: 0 0 auto;
  display: flex;
}

/*
  IMPORTANT:
  LandingHero may ship with its own fixed max-width. That prevents the wrapper
  from visually expanding when switching to traditional search mode.
  Force the component root to be width:100% and remove any internal max-width.
*/
.landing-view__hero > :deep(*) {
  width: 100% !important;
  max-width: none !important;
}

.landing-view--traditional .landing-view__hero {
  margin-bottom: 0.65rem;
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
  width: 100%;
  margin: 0.15rem 0 0;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding: 0 0 0.75rem;
  display: flex;
}

.landing-view--traditional .landing-view__archives {
  margin-top: 0.05rem;
}

.landing-view__archives-panel {
  flex: 1 1 auto;
  min-height: 320px;
  height: 100%;
  background: rgba(255, 255, 255, 0.88);
  border-radius: 20px;
  box-shadow: 0 20px 55px rgba(28, 39, 84, 0.14);
  overflow: auto;
  position: relative;
}

.landing-view__archives-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1.25rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: rgba(28, 39, 84, 0.55);
  pointer-events: none;
}

/* Smooth width change when toggling modes */
.landing-view--ready .landing-view__content {
  transition: max-width 400ms cubic-bezier(0.2, 0.8, 0.2, 1);
  will-change: max-width;
}

/* Search bar fade */
.landing-hero-enter-active,
.landing-hero-leave-active {
  transition: opacity 220ms ease, transform 220ms ease;
}

.landing-hero-enter-from,
.landing-hero-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.landing-hero-enter-to,
.landing-hero-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* Results area fade */
.landing-archives-enter-active,
.landing-archives-leave-active {
  transition: opacity 500ms ease;
  will-change: opacity;
  transform: translateZ(0);
}

.landing-archives-enter-from,
.landing-archives-leave-to {
  opacity: 0;
}

.landing-archives-enter-to,
.landing-archives-leave-from {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .landing-view--ready .landing-view__content,
  .landing-hero-enter-active,
  .landing-hero-leave-active,
  .landing-archives-enter-active,
  .landing-archives-leave-active {
    transition: none !important;
  }
}

:deep(.landing-view__archives-table) {
  height: 100%;
  min-height: 100%;
}

.landing-view__archives-panel::-webkit-scrollbar {
  width: 8px;
}

.landing-view__archives-panel::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.2);
  border-radius: 999px;
}

.landing-view__archives-panel::-webkit-scrollbar-track {
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