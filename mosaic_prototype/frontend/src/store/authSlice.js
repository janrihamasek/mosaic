import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  getAuthState,
  login as authLogin,
  register as authRegister,
  logout as authLogout,
} from '../services/authService';

const DEFAULT_STATE = {
  isAuthenticated: false,
  accessToken: null,
  csrfToken: null,
  username: null,
  tokenType: 'Bearer',
  expiresAt: 0,
};

const persisted = getAuthState();

const initialState = {
  ...DEFAULT_STATE,
  ...persisted,
  status: {
    login: 'idle',
    register: 'idle',
    logout: 'idle',
  },
  error: null,
};

function applyAuthState(target, payload) {
  const next = payload || DEFAULT_STATE;
  target.isAuthenticated = Boolean(next.isAuthenticated);
  target.accessToken = next.accessToken ?? null;
  target.csrfToken = next.csrfToken ?? null;
  target.username = next.username ?? null;
  target.tokenType = next.tokenType ?? 'Bearer';
  target.expiresAt = next.expiresAt ?? 0;
}

function serialiseError(error) {
  if (!error) return null;
  return {
    code: error.code,
    message: error.message,
    friendlyMessage: error.friendlyMessage,
    details: error.details,
  };
}

export const login = createAsyncThunk(
  'auth/login',
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const result = await authLogin(username, password);
      return result;
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const register = createAsyncThunk(
  'auth/register',
  async ({ username, password }, { rejectWithValue }) => {
    try {
      await authRegister(username, password);
      return { ok: true };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async ({ silent = true } = {}, { rejectWithValue }) => {
    try {
      authLogout({ silent });
      return { silent };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const hydrateAuthFromStorage = createAsyncThunk(
  'auth/hydrateFromStorage',
  async () => {
    return getAuthState();
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuthState(state, action) {
      applyAuthState(state, action.payload);
      state.error = null;
    },
    clearAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status.login = 'loading';
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status.login = 'succeeded';
        applyAuthState(state, action.payload);
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.status.login = 'failed';
        state.error = action.payload || serialiseError(action.error);
      })
      .addCase(register.pending, (state) => {
        state.status.register = 'loading';
        state.error = null;
      })
      .addCase(register.fulfilled, (state) => {
        state.status.register = 'succeeded';
      })
      .addCase(register.rejected, (state, action) => {
        state.status.register = 'failed';
        state.error = action.payload || serialiseError(action.error);
      })
      .addCase(logout.pending, (state) => {
        state.status.logout = 'loading';
        state.error = null;
      })
      .addCase(logout.fulfilled, (state) => {
        state.status.logout = 'succeeded';
        applyAuthState(state, DEFAULT_STATE);
        state.error = null;
      })
      .addCase(logout.rejected, (state, action) => {
        state.status.logout = 'failed';
        state.error = action.payload || serialiseError(action.error);
      })
      .addCase(hydrateAuthFromStorage.fulfilled, (state, action) => {
        applyAuthState(state, action.payload);
      });
  },
});

export const { setAuthState, clearAuthError } = authSlice.actions;

export const selectAuth = (state) => state.auth;
export const selectIsAuthenticated = (state) => Boolean(state.auth.isAuthenticated);

export default authSlice.reducer;
