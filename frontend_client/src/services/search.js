import { apiClient } from './api';

export async function searchArchives({ query, domainIds, mode, page, pageSize }) {
  const params = {
    q: query,
    page: page ?? 1,
    page_size: pageSize ?? 10,
    mode,
    domain_ids: Array.isArray(domainIds) && domainIds.length ? domainIds.join(',') : undefined
  };

  const response = await apiClient.get('/search/archives', { params });
  return response.data;
}

