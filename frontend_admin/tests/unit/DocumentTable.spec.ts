import { RouterLinkStub, mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import DocumentTable from '@/components/DocumentTable.vue';

describe('DocumentTable', () => {
  const documents = [
    {
      id: 1,
      title: 'B Document',
      created_at: '2024-01-01',
      updated_at: '2024-01-05',
      domain_id: 1,
      doc_metadata: {},
      uuid: 'doc-1'
    },
    {
      id: 2,
      title: 'A Document',
      created_at: '2024-02-01',
      updated_at: '2024-02-06',
      domain_id: 2,
      doc_metadata: {},
      uuid: 'doc-2'
    }
  ];

  it('emits sort changes', async () => {
    const wrapper = mount(DocumentTable, {
      props: {
        documents,
        sortBy: 'created_at',
        sortDirection: 'desc'
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub
        }
      }
    });

    await wrapper.findAll('th button')[0].trigger('click');

    expect(wrapper.emitted('update:sort')).toBeTruthy();
    const [[payload]] = wrapper.emitted('update:sort');
    expect(payload.sortBy).toBe('title');
    expect(payload.sortDirection).toBe('asc');
  });
});
