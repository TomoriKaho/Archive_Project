import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import StructuredViewer from '../../../frontend_shared/components/structured/StructuredViewer.vue';

describe('StructuredViewer', () => {
  it('renders nested object structure', () => {
    const wrapper = mount(StructuredViewer, {
      props: {
        value: {
          title: 'Test Document',
          meta: { year: 2024 }
        }
      }
    });

    expect(wrapper.text()).toContain('title');
    expect(wrapper.text()).toContain('Test Document');
    expect(wrapper.text()).toContain('meta');
    expect(wrapper.text()).toContain('2024');
  });

  it('falls back to plain text for primitive values', () => {
    const wrapper = mount(StructuredViewer, {
      props: {
        value: 'plain text cell'
      }
    });

    expect(wrapper.text()).toContain('plain text cell');
  });
});
