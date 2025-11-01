import {
  createAsyncThunk,
  createSlice,
  type Draft,
  type PayloadAction,
} from "@reduxjs/toolkit";

import {
  getAuthState,
  login as authLogin,
  register as authRegister,
  logout as authLogout,
} from "../services/authService";
import type { RootState } from "./index";
import type { AuthState, FriendlyError } from "../types/store";

type AuthPayload = Partial<Omit<AuthState, "status" | "error">>;

const DEFAULT_STATE: Omit<AuthState, "status" | "error"> = {
  isAuthenticated: false,
  accessToken: null,
  csrfToken: null,
  username: null,
  tokenType: "Bearer",
  expiresAt: 0,
};

const persisted = getAuthState() as AuthPayload | null;

const initialState: AuthState = {
  ...DEFAULT_STATE,
  ...(persisted ?? {}),
  status: {
    login: "idle",
    register: "idle",
    logout: "idle",
  },
  error: null,
};

function applyAuthState(target: Draft<AuthState>, payload: AuthPayload | null | undefined) {
  const next = payload || DEFAULT_STATE;
  target.isAuthenticated = Boolean(next.isAuthenticated);
  target.accessToken = (next.accessToken ?? null) as AuthState["accessToken"];
  target.csrfToken = (next.csrfToken ?? null) as AuthState["csrfToken"];
  target.username = (next.username ?? null) as AuthState["username"];
  target.tokenType = next.tokenType ?? "Bearer";
  target.expiresAt = next.expiresAt ?? 0;
}

function serialiseError(error: unknown): FriendlyError | null {
  if (!error) return null;
  const err = error as FriendlyError & { message?: string };
  return {
    code: err.code,
    message: err.message,
    friendlyMessage: err.friendlyMessage,
    details: err.details,
  };
}

export const login = createAsyncThunk<
  AuthPayload,
  { username: string; password: string },
  { rejectValue: FriendlyError }
>("auth/login", async ({ username, password }, { rejectWithValue }) => {
  try {
    const result = await authLogin(username, password);
    return result as AuthPayload;
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
});

export const register = createAsyncThunk<
  { ok: boolean },
  { username: string; password: string },
  { rejectValue: FriendlyError }
>("auth/register", async ({ username, password }, { rejectWithValue }) => {
  try {
    await authRegister(username, password);
    return { ok: true };
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
});

export const logout = createAsyncThunk<
  { silent: boolean },
  { silent?: boolean } | undefined,
  { rejectValue: FriendlyError }
>("auth/logout", async ({ silent = true } = {}, { rejectWithValue }) => {
  try {
    authLogout({ silent });
    return { silent };
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
});

export const hydrateAuthFromStorage = createAsyncThunk<AuthPayload>("auth/hydrateFromStorage", async () => {
  return getAuthState() as AuthPayload;
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setAuthState(state, action: PayloadAction<AuthPayload | null>) {
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
        state.status.login = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status.login = "succeeded";
        applyAuthState(state, action.payload);
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.status.login = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(register.pending, (state) => {
        state.status.register = "loading";
        state.error = null;
      })
      .addCase(register.fulfilled, (state) => {
        state.status.register = "succeeded";
      })
      .addCase(register.rejected, (state, action) => {
        state.status.register = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(logout.pending, (state) => {
        state.status.logout = "loading";
        state.error = null;
      })
      .addCase(logout.fulfilled, (state) => {
        state.status.logout = "succeeded";
        applyAuthState(state, DEFAULT_STATE);
        state.error = null;
      })
      .addCase(logout.rejected, (state, action) => {
        state.status.logout = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(hydrateAuthFromStorage.fulfilled, (state, action) => {
        applyAuthState(state, action.payload);
      });
  },
});

export const { setAuthState, clearAuthError } = authSlice.actions;

export const selectAuth = (state: RootState) => state.auth;
export const selectIsAuthenticated = (state: RootState) => Boolean(state.auth.isAuthenticated);

export default authSlice.reducer;
