import type { Activity, Entry, StatsSnapshot } from "./api";

export type AsyncRequestStatus = "idle" | "loading" | "succeeded" | "failed";

export interface FriendlyError {
  code?: string;
  message?: string;
  friendlyMessage?: string;
  details?: any;
}

export interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  csrfToken: string | null;
  username: string | null;
  tokenType: string;
  expiresAt: number;
  status: {
    login: AsyncRequestStatus;
    register: AsyncRequestStatus;
    logout: AsyncRequestStatus;
  };
  error: FriendlyError | null;
}

export interface EntriesFilters {
  startDate: string | null;
  endDate: string | null;
  activity: string;
  category: string;
}

export interface TodayRow {
  id?: number;
  name: string;
  category: string;
  value: number;
  note: string;
  goal: number;
  [key: string]: unknown;
}

export interface EntriesState {
  items: Entry[];
  filters: EntriesFilters;
  status: AsyncRequestStatus;
  deletingId: number | null;
  error: FriendlyError | null;
  importStatus: AsyncRequestStatus;
  today: {
    date: string;
    rows: TodayRow[];
    status: AsyncRequestStatus;
    error: FriendlyError | null;
    dirty: Record<string, TodayRow>;
    savingStatus: AsyncRequestStatus;
    saveError: FriendlyError | null;
  };
  stats: {
    snapshot: StatsSnapshot | null;
    status: AsyncRequestStatus;
    error: FriendlyError | null;
    date: string | null;
  };
  finalizeStatus: AsyncRequestStatus;
}

export interface ActivitiesState {
  all: Activity[];
  active: Activity[];
  status: AsyncRequestStatus;
  error: FriendlyError | null;
  mutationStatus: AsyncRequestStatus;
  mutationError: FriendlyError | null;
  selectedActivityId: number | null;
}

export {};
