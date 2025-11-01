import axios from 'axios';
import { API_BASE_URL } from '../config';

const STORAGE_KEY = 'mosaic.auth';
const authClient = axios.create({ baseURL: API_BASE_URL });
const listeners = new Set();

const ERROR_MESSAGES = {
  invalid_credentials: 'Neplatné přihlašovací údaje',
  unauthorized: 'Je třeba se přihlásit',
  invalid_csrf: 'Neplatný CSRF token',
  too_many_requests: 'Příliš mnoho pokusů, zkuste to později',
  rate_limited: 'Příliš mnoho pokusů, zkuste to později',
  token_expired: 'Relace vypršela, přihlaste se znovu',
};

function notify() {
  const state = getAuthState();
  listeners.forEach((listener) => listener(state));
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (err) {
    console.warn('Failed to parse auth storage', err);
    return null;
  }
}

function persist(auth) {
  if (!auth) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
}

function buildError(error) {
  const payload = error?.response?.data?.error;
  const err = new Error(payload?.message || error?.message || 'Request failed');
  if (payload?.code) {
    err.code = payload.code;
    err.friendlyMessage = ERROR_MESSAGES[payload.code] || payload.message;
    err.details = payload.details;
  }
  return err;
}

function normaliseAuth(username, responseData) {
  const { access_token: accessToken, csrf_token: csrfToken, token_type: tokenType = 'Bearer', expires_in: expiresIn } = responseData;
  const expiresAt = Date.now() + Number(expiresIn || 0) * 1000;
  return {
    username,
    accessToken,
    csrfToken,
    tokenType,
    expiresAt,
  };
}

export function getAuthState() {
  const stored = readStorage();
  if (!stored || !stored.accessToken || !stored.csrfToken) {
    persist(null);
    return { isAuthenticated: false, accessToken: null, csrfToken: null, username: null, tokenType: 'Bearer', expiresAt: 0 };
  }
  if (stored.expiresAt && stored.expiresAt <= Date.now()) {
    persist(null);
    return { isAuthenticated: false, accessToken: null, csrfToken: null, username: null, tokenType: 'Bearer', expiresAt: 0 };
  }
  return { ...stored, isAuthenticated: true };
}

export async function login(username, password) {
  try {
    const response = await authClient.post('/login', { username, password });
    const auth = normaliseAuth(username, response.data);
    persist(auth);
    notify();
    return { ...auth, isAuthenticated: true };
  } catch (error) {
    throw buildError(error);
  }
}

export async function register(username, password) {
  try {
    await authClient.post('/register', { username, password });
  } catch (error) {
    throw buildError(error);
  }
}

export function logout({ silent } = { silent: false }) {
  persist(null);
  notify();
  if (!silent) {
    window.location.assign('/login');
  }
}

export function getAuthHeaders() {
  const state = getAuthState();
  if (!state.isAuthenticated) {
    return {};
  }
  const headers = {
    Authorization: `${state.tokenType || 'Bearer'} ${state.accessToken}`,
  };
  if (state.csrfToken) {
    headers['X-CSRF-Token'] = state.csrfToken;
  }
  return headers;
}

export function isTokenExpired() {
  const state = getAuthState();
  if (!state.isAuthenticated) return true;
  return state.expiresAt <= Date.now();
}

export async function refreshToken() {
  const state = getAuthState();
  if (!state.isAuthenticated) {
    const err = new Error('Unauthenticated');
    err.code = 'unauthorized';
    throw err;
  }
  if (state.expiresAt <= Date.now()) {
    logout({ silent: true });
    const err = new Error('Session expired');
    err.code = 'token_expired';
    err.friendlyMessage = ERROR_MESSAGES.token_expired;
    throw err;
  }
  return state;
}

export function getFriendlyMessage(code, fallback) {
  if (!code) return fallback;
  return ERROR_MESSAGES[code] || fallback;
}

// Legacy helper for consumers that just need basic auth props
export function getTokens() {
  const state = getAuthState();
  if (!state.isAuthenticated) return null;
  const { accessToken, csrfToken, tokenType, expiresAt, username } = state;
  return { accessToken, csrfToken, tokenType, expiresAt, username };
}

export function getAccessToken() {
  const tokens = getTokens();
  return tokens?.accessToken || null;
}

export function getCsrfToken() {
  const tokens = getTokens();
  return tokens?.csrfToken || null;
}

// Support window storage sync (multiple tabs)
window.addEventListener('storage', (event) => {
  if (event.key === STORAGE_KEY) {
    notify();
  }
});
