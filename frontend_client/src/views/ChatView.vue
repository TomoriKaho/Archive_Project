<template>
  <div class="chat-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>历史会话</h2>
        <button class="home-button" @click="goHome">主页</button>
      </div>
      <ConversationList
        :conversations="conversations"
        :active-id="activeConversationId"
        @select="selectConversation"
      />
    </aside>

    <main class="chat-area">
      <header class="chat-header">
        <div class="chat-title">
          <h1>{{ activeConversation?.title || '新会话' }}</h1>
          <p v-if="activeConversation?.updatedAt" class="meta">
            最近更新：{{ activeConversation.updatedAt }}
          </p>
        </div>
      </header>

      <ChatMessages :messages="activeConversation?.messages || messages" />

      <ChatComposer
        :placeholder="composerPlaceholder"
        :initial-query="initialQuery"
        @send="handleSend"
      />
    </main>
  </div>
</template>

<script>
import ConversationList from '@/components/ConversationList.vue';
import ChatMessages from '@/components/ChatMessages.vue';
import ChatComposer from '@/components/ChatComposer.vue';

export default {
  name: 'ChatView',
  components: {
    ConversationList,
    ChatMessages,
    ChatComposer
  },
  props: {
    initialQuery: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      conversations: [
        {
          id: '1',
          title: '示例：如何上传档案',
          updatedAt: '2024-07-10 09:15',
          messages: [
            { role: 'user', content: '如何上传一份新的档案？' },
            {
              role: 'assistant',
              content:
                '在左侧菜单选择“档案管理”，点击右上角“上传档案”，按照指引填写信息并上传文件即可。'
            }
          ]
        },
        {
          id: '2',
          title: '示例：检索历史对话',
          updatedAt: '2024-07-08 15:30'
        }
      ],
      activeConversationId: '1',
      messages: [
        { role: 'assistant', content: '您好，我是 Archive 助手，很高兴为您服务。' }
      ]
    };
  },
  computed: {
    activeConversation() {
      return this.conversations.find(
        conversation => conversation.id === this.activeConversationId
      );
    },
    composerPlaceholder() {
      return this.activeConversation
        ? '继续提问或补充上下文…'
        : '请输入您的问题…';
    }
  },
  watch: {
    initialQuery: {
      immediate: true,
      handler(query) {
        if (query) {
          this.messages = [
            { role: 'user', content: query },
            {
              role: 'assistant',
              content: '已收到您的问题，正在为您检索相关资料…'
            }
          ];
          this.activeConversationId = null;
        }
      }
    }
  },
  methods: {
    goHome() {
      this.$router.push({ name: 'home' });
    },
    selectConversation(id) {
      this.activeConversationId = id;
    },
    handleSend(content) {
      if (!content) {
        return;
      }
      const normalizedContent = content.trim();
      const baseConversation =
        this.activeConversation ||
        ({
          id: `draft-${Date.now()}`,
          title: normalizedContent.slice(0, 16) || '临时会话',
          updatedAt: new Date().toLocaleString(),
          messages: []
        });

      baseConversation.messages = [
        ...(baseConversation.messages || []),
        { role: 'user', content: normalizedContent },
        {
          role: 'assistant',
          content: '（示例回复）稍后将接入真实对话接口。'
        }
      ];

      if (!this.activeConversation) {
        this.conversations = [baseConversation, ...this.conversations];
        this.activeConversationId = baseConversation.id;
      } else {
        this.conversations = this.conversations.map(conversation =>
          conversation.id === baseConversation.id ? baseConversation : conversation
        );
      }
    }
  }
};
</script>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  height: 100vh;
  background: #f1f5f9;
}

.sidebar {
  background: #10172a;
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  gap: 1.5rem;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.1rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.home-button {
  border: 1px solid rgba(248, 250, 252, 0.4);
  background: transparent;
  color: inherit;
  border-radius: 999px;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.home-button:hover {
  background: rgba(148, 163, 184, 0.2);
}

.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.chat-header {
  padding: 1.25rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.chat-title h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #111827;
}

.meta {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }
}
</style>
