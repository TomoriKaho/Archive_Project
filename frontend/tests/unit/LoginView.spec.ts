import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';
import { describe, expect, it, vi } from 'vitest';

import LoginView from '@/views/LoginView.vue';
import { useAuthStore } from '@/store/auth';

vi.mock('vue-router', () => ({
  createRouter: () => ({
    beforeEach: vi.fn(),
    afterEach: vi.fn()
  }),
  createWebHistory: vi.fn(),
  useRouter: () => ({
    push: vi.fn(),
    currentRoute: {
      value: {
        query: {}
      }
    }
  }),
  RouterLink: {
    name: 'RouterLink',
    props: ['to'],
    template: '<a :href="to">\n    <slot />\n  </a>'
  }
}));

describe('LoginView', () => {
  it('shows validation errors for invalid input', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })]
      }
    });

    await wrapper.find('form').trigger('submit.prevent');

    expect(wrapper.text()).toContain('Email is required.');
    expect(wrapper.text()).toContain('Password is required.');
  });

  it('submits valid credentials', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })]
      }
    });

    const authStore = useAuthStore();
    authStore.login = vi.fn().mockResolvedValue({});

    await wrapper.find('#email').setValue('user@example.com');
    await wrapper.find('#password').setValue('StrongPass1');
    await wrapper.find('form').trigger('submit.prevent');

    expect(authStore.login).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'StrongPass1'
    });
  });
});
