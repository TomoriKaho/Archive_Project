import { apiClient } from './api';

export async function fetchArchiveAssets(archiveId) {
  const response = await apiClient.get(`/archives/${archiveId}/assets`);
  return response.data;
}

export async function downloadArchiveAsset(asset) {
  const response = await apiClient.get(`/archive-assets/${asset.id}/download`, {
    responseType: 'blob'
  });
  const objectUrl = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = asset.filename || 'archive-file';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
