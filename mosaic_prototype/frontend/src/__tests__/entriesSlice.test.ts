import { AnyAction, configureStore } from '@reduxjs/toolkit';
import entriesReducer, { loadEntries } from '../store/entriesSlice';
import * as api from '../api';
import type { ActivitiesState, AuthState } from '../types/store';

jest.mock('../api', () => ({
  fetchEntries: jest.fn(),
  deleteEntry: jest.fn(),
  addEntry: jest.fn(),
  fetchToday: jest.fn(),
  finalizeDay: jest.fn(),
  fetchProgressStats: jest.fn(),
  importEntriesCsv: jest.fn(),
}));

const mockedFetchEntries = api.fetchEntries as unknown as jest.Mock;

const authInitialState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  csrfToken: null,
  username: null,
  displayName: null,
  isAdmin: false,
  userId: null,
  tokenType: 'Bearer',
  expiresAt: 0,
  status: {
    login: 'idle',
    register: 'idle',
    logout: 'idle',
    profile: 'idle',
    profileUpdate: 'idle',
    deleteAccount: 'idle',
  },
  error: null,
};

const activitiesInitialState: ActivitiesState = {
  all: [],
  active: [],
  status: 'idle',
  error: null,
  mutationStatus: 'idle',
  mutationError: null,
  selectedActivityId: null,
};

describe('entriesSlice async thunks', () => {
  it('transitions from loading to succeeded when loadEntries resolves', async () => {
    mockedFetchEntries.mockResolvedValue([{ id: 1, activity: 'Read', date: '2024-01-01', value: 1 }]);

    const store = configureStore({
      reducer: {
        auth: (state: AuthState = authInitialState) => state,
        entries: entriesReducer,
        activities: (state: ActivitiesState = activitiesInitialState) => state,
      },
    });

    const dispatchPromise = store.dispatch(loadEntries({}) as unknown as AnyAction);

    expect(store.getState().entries.status).toBe('loading');

    await dispatchPromise;

    const state = store.getState().entries;
    expect(state.status).toBe('succeeded');
    expect(state.items).toHaveLength(1);
    expect(state.items[0]).toMatchObject({ id: 1, activity: 'Read' });
  });
});
