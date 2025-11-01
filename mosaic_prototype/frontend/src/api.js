import apiClient from './apiClient';
import { API_BASE_URL as API_BASE } from './config';

function extractParams(filters = {}) {
  const params = new URLSearchParams();
  if (filters.startDate) params.set('start_date', filters.startDate);
  if (filters.endDate) params.set('end_date', filters.endDate);
  if (filters.activity && filters.activity !== 'all') params.set('activity', filters.activity);
  if (filters.category && filters.category !== 'all') params.set('category', filters.category);
  return params;
}

// --- ENTRIES ---
export async function fetchEntries(filters = {}) {
  const params = Object.fromEntries(extractParams(filters));
  const response = await apiClient.get('/entries', { params });
  return response.data;
}

export async function addEntry(entry) {
  const response = await apiClient.post('/add_entry', entry);
  return response.data;
}

export async function deleteEntry(id) {
  const response = await apiClient.delete(`/entries/${id}`);
  return response.data;
}

// --- ACTIVITIES ---
export async function fetchActivities({ all = false } = {}) {
  const response = await apiClient.get('/activities', { params: all ? { all: 'true' } : {} });
  return response.data;
}

export async function addActivity(activity) {
  const response = await apiClient.post('/add_activity', activity);
  return response.data;
}

export async function updateActivity(id, payload) {
  const response = await apiClient.put(`/activities/${id}`, payload);
  return response.data;
}

export async function deactivateActivity(id) {
  const response = await apiClient.patch(`/activities/${id}/deactivate`);
  return response.data;
}

export async function activateActivity(id) {
  const response = await apiClient.patch(`/activities/${id}/activate`);
  return response.data;
}

export async function deleteActivity(id) {
  const response = await apiClient.delete(`/activities/${id}`);
  return response.data;
}

// --- STATS ---
export async function fetchProgressStats({ date } = {}) {
  const params = {};
  if (date) params.date = date;
  const response = await apiClient.get('/stats/progress', { params });
  return response.data;
}

// --- TODAY ---
export async function fetchToday(dateStr) {
  const params = dateStr ? { date: dateStr } : {};
  const response = await apiClient.get('/today', { params });
  return response.data;
}

export async function finalizeDay(dateStr) {
  const response = await apiClient.post('/finalize_day', { date: dateStr });
  return response.data;
}

// --- IMPORT ---
export async function importEntriesCsv(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post('/import_csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export const getStreamProxyUrl = (url, username, password) =>
  `${API_BASE}/api/stream-proxy?url=${encodeURIComponent(url)}&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
