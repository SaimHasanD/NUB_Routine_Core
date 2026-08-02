// API service layer

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export async function healthCheck() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function fetchAdminStatus() {
  const res = await fetch(`${BASE_URL}/admin/status`);
  if (!res.ok) throw new Error('Failed to fetch admin status');
  return res.json();
}

export async function fetchGroups() {
  const res = await fetch(`${BASE_URL}/groups`);
  if (!res.ok) throw new Error('Failed to fetch groups');
  return res.json();
}

export function getSourceFileUrl() {
  return `${BASE_URL}/source-file`;
}



export async function fetchRoutine(groupId) {
  const res = await fetch(`${BASE_URL}/routine/${groupId}`);
  if (!res.ok) throw new Error(`Failed to fetch routine for ${groupId}`);
  return res.json();
}

export async function uploadExcel(file, password, replace = false) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('password', password || '');
  formData.append('replace', replace ? 'true' : 'false');
  const res = await fetch(`${BASE_URL}/upload`, { method: 'POST', body: formData });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getExamSchedule() {
  const res = await fetch(`${BASE_URL}/exam`);
  if (!res.ok) throw new Error('No exam schedule found');
  return res.json();
}

export async function uploadExamSchedule(file, password) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('password', password || '');
  const res = await fetch(`${BASE_URL}/exam/upload`, { method: 'POST', body: formData });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}


