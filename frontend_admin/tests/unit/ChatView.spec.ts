import { flushPromises } from '@vue/test-utils';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ChatView from '@/views/ChatView.vue';
import { useChatStore } from '@/store/chat';
import { useDomainsStore } from '@/store/domains';

const BaseModalStub = {
  name: 'BaseModal',
  props: ['modelValue', 'title'],
  emits: ['update:modelValue'],
  template: `<div v-if="modelValue" class="modal-stub"><slot /><slot name="footer" /></div>`
};

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('opens modal and starts conversation', async () => {
    const pinia = createTestingPinia({
      createSpy: vi.fn,
      stubActions: false
    });
    const chatStore = useChatStore(pinia);
    chatStore.loadConversations = vi.fn().mockResolvedValue(undefined);
    chatStore.startConversation = vi.fn().mockResolvedValue(undefined);
    const domainsStore = useDomainsStore(pinia);
    domainsStore.loadDomains = vi.fn().mockResolvedValue(undefined);

    const wrapper = mount(ChatView, {
      global: {
        plugins: [pinia],
        stubs: {
          BaseModal: BaseModalStub
        }
      }
    });

    await flushPromises();

    await wrapper.find('.chat__header .button').trigger('click');
    expect(wrapper.find('.modal-stub').exists()).toBe(true);

    await wrapper.find('#conversation-name').setValue('Research Thread');
    await wrapper.find('#conversation-prompt').setValue('Let us discuss.');
    await wrapper.find('.modal-stub .button--primary').trigger('click');

    expect(chatStore.startConversation).toHaveBeenCalledWith({
      name: 'Research Thread',
      prompt: 'Let us discuss.',
      domain_ids: []
    });
  });
});
