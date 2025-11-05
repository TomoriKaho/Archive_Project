import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import DocumentTable from '@/components/DocumentTable.vue';

describe('DocumentTable', () => {
  const documents = [
    { id: 1, title: 'B Document', created_at: '2024-01-01', owner: { name: 'Alice' }, tags: ['a'] },
    { id: 2, title: 'A Document', created_at: '2024-02-01', owner: { name: 'Bob' }, tags: ['b'] }
  ];

  it('emits sort changes', async () => {
    const wrapper = mount(DocumentTable, {
      props: {
        documents,
        sortBy: 'created_at',
        sortDirection: 'desc'
      }
    });

    await wrapper.findAll('th button')[0].trigger('click');

    expect(wrapper.emitted('update:sort')).toBeTruthy();
    const [[payload]] = wrapper.emitted('update:sort');
    expect(payload.sortBy).toBe('title');
    expect(payload.sortDirection).toBe('asc');
  });
});
