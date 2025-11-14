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
  updateStoredAuth,
} from "../services/authService";
import { fetchCurrentUser, updateCurrentUser, deleteCurrentUser } from "../services/userService";
import type { RootState } from "./index";
import type { AuthState, FriendlyError } from "../types/store";

type AuthPayload = Partial<Omit<AuthState, "status" | "error">>;

const DEFAULT_STATE: Omit<AuthState, "status" | "error"> = {
  isAuthenticated: false,
  accessToken: null,
  csrfToken: null,
  username: null,
  displayName: null,
  isAdmin: false,
  userId: null,
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
    profile: "idle",
    profileUpdate: "idle",
    deleteAccount: "idle",
  },
  error: null,
};

function applyAuthState(target: Draft<AuthState>, payload: AuthPayload | null | undefined) {
  const source = payload ?? DEFAULT_STATE;
  const pick = <T>(value: T | undefined, fallback: T): T =>
    value !== undefined ? value : fallback;

  target.isAuthenticated =
    source.isAuthenticated !== undefined
      ? Boolean(source.isAuthenticated)
      : Boolean(target.isAuthenticated);
  target.accessToken = pick(
    (source.accessToken ?? undefined) as AuthState["accessToken"],
    target.accessToken ?? null
  );
  target.csrfToken = pick(
    (source.csrfToken ?? undefined) as AuthState["csrfToken"],
    target.csrfToken ?? null
  );
  target.username = pick(
    (source.username ?? undefined) as AuthState["username"],
    target.username ?? null
  );
  target.displayName = pick(
    (source.displayName ?? undefined) as AuthState["displayName"],
    target.displayName ?? null
  );
  target.isAdmin = pick(source.isAdmin ?? undefined, target.isAdmin ?? false) ? true : false;
  target.userId = pick(
    (source.userId ?? undefined) as AuthState["userId"],
    target.userId ?? null
  );
  target.tokenType = pick(source.tokenType ?? undefined, target.tokenType ?? "Bearer") || "Bearer";
  target.expiresAt = pick(source.expiresAt ?? undefined, target.expiresAt ?? 0) ?? 0;
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
  { username: string; password: string; displayName?: string },
  { rejectValue: FriendlyError }
>("auth/register", async ({ username, password, displayName }, { rejectWithValue }) => {
  try {
    await authRegister(username, password, displayName);
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

export const fetchCurrentUserProfile = createAsyncThunk<
  AuthPayload,
  void,
  { rejectValue: FriendlyError }
>("auth/fetchCurrentUserProfile", async (_arg, { rejectWithValue }) => {
  try {
    const data = await fetchCurrentUser();
    const payload: AuthPayload = {
      userId: data?.id ?? null,
      username: data?.username ?? null,
      displayName: data?.display_name ?? data?.username ?? null,
      isAdmin: Boolean(data?.is_admin),
    };
    updateStoredAuth(payload);
    return payload;
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
});

export const updateCurrentUserProfile = createAsyncThunk<
  AuthPayload,
  { displayName?: string | null; password?: string | null },
  { rejectValue: FriendlyError }
>("auth/updateCurrentUserProfile", async ({ displayName, password }, { rejectWithValue }) => {
  try {
    const payload: Record<string, string> = {};
    if (displayName != null) {
      payload.display_name = displayName;
    }
    if (password != null) {
      payload.password = password;
    }
    const data = await updateCurrentUser(payload);
    const user = data?.user ?? {};
    const nextState: AuthPayload = {
      userId: user?.id ?? null,
      username: user?.username ?? null,
      displayName: user?.display_name ?? user?.username ?? null,
      isAdmin: Boolean(user?.is_admin),
    };
    updateStoredAuth(nextState);
    return nextState;
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
});

export const deleteAccount = createAsyncThunk<
  void,
  void,
  { rejectValue: FriendlyError }
>("auth/deleteAccount", async (_arg, { rejectWithValue }) => {
  try {
    await deleteCurrentUser();
    authLogout({ silent: true });
  } catch (error) {
    const reject = serialiseError(error) ?? {};
    return rejectWithValue(reject);
  }
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
        state.status.profile = "idle";
        state.status.profileUpdate = "idle";
        state.status.deleteAccount = "idle";
      })
      .addCase(logout.rejected, (state, action) => {
        state.status.logout = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(hydrateAuthFromStorage.fulfilled, (state, action) => {
        applyAuthState(state, action.payload);
      })
      .addCase(fetchCurrentUserProfile.pending, (state) => {
        state.status.profile = "loading";
      })
      .addCase(fetchCurrentUserProfile.fulfilled, (state, action) => {
        state.status.profile = "succeeded";
        applyAuthState(state, { ...action.payload, isAuthenticated: true });
      })
      .addCase(fetchCurrentUserProfile.rejected, (state, action) => {
        state.status.profile = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(updateCurrentUserProfile.pending, (state) => {
        state.status.profileUpdate = "loading";
      })
      .addCase(updateCurrentUserProfile.fulfilled, (state, action) => {
        state.status.profileUpdate = "succeeded";
        applyAuthState(state, { ...action.payload, isAuthenticated: true });
        state.error = null;
      })
      .addCase(updateCurrentUserProfile.rejected, (state, action) => {
        state.status.profileUpdate = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(deleteAccount.pending, (state) => {
        state.status.deleteAccount = "loading";
      })
      .addCase(deleteAccount.fulfilled, (state) => {
        state.status.deleteAccount = "succeeded";
        applyAuthState(state, DEFAULT_STATE);
        state.error = null;
      })
      .addCase(deleteAccount.rejected, (state, action) => {
        state.status.deleteAccount = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      });
  },
});

export const { setAuthState, clearAuthError } = authSlice.actions;

export const selectAuth = (state: RootState) => state.auth;
export const selectIsAuthenticated = (state: RootState) => Boolean(state.auth.isAuthenticated);
export const selectIsAdmin = (state: RootState) => Boolean(state.auth.isAdmin);

export default authSlice.reducer;
