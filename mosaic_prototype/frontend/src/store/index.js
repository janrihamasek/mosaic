import { configureStore } from '@reduxjs/toolkit';
import authReducer, { setAuthState } from './authSlice';
import entriesReducer from './entriesSlice';
import activitiesReducer from './activitiesSlice';
import { subscribe as subscribeAuthChanges, getAuthState } from '../services/authService';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    entries: entriesReducer,
    activities: activitiesReducer,
  },
});

// Sync auth storage updates (login/logout in other tabs)
const unsubscribeAuth = subscribeAuthChanges((state) => {
  store.dispatch(setAuthState(state));
});
void unsubscribeAuth;

// Ensure latest state on initial load
store.dispatch(setAuthState(getAuthState()));

export const dispatch = store.dispatch;
export const getState = store.getState;
