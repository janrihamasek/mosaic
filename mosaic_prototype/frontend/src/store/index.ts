import {
  configureStore,
  type AnyAction,
  type ThunkAction,
} from "@reduxjs/toolkit";

import authReducer, { setAuthState } from "./authSlice";
import entriesReducer from "./entriesSlice";
import activitiesReducer from "./activitiesSlice";
import { subscribe as subscribeAuthChanges, getAuthState } from "../services/authService";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    entries: entriesReducer,
    activities: activitiesReducer,
  },
});

// Sync auth storage updates (login/logout in other tabs)
const unsubscribeAuth = subscribeAuthChanges((state: unknown) => {
  store.dispatch(setAuthState(state));
});
void unsubscribeAuth;

// Ensure latest state on initial load
store.dispatch(setAuthState(getAuthState()));

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const dispatch: AppDispatch = store.dispatch;
export const getState = store.getState;

export type AppThunk<ReturnType = void> = ThunkAction<ReturnType, RootState, unknown, AnyAction>;
