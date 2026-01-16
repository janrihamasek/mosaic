import type { Activity, Entry, StatsSnapshot, ActivityType } from "./api";

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
  displayName: string | null;
  isAdmin: boolean;
  userId: number | null;
  tokenType: string;
  expiresAt: number;
  status: {
    login: AsyncRequestStatus;
    register: AsyncRequestStatus;
    logout: AsyncRequestStatus;
    profile: AsyncRequestStatus;
    profileUpdate: AsyncRequestStatus;
    deleteAccount: AsyncRequestStatus;
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
  activity_type: ActivityType;
  [key: string]: unknown;
}

export interface CalendarCell {
  date: string;
  value: number;
  note?: string;
  entry_id?: number;
}

export interface CalendarRow {
  name: string;
  category: string;
  goal: number;
  activity_type: ActivityType;
  active?: boolean;
  deactivated_at?: string | null;
  cells: Record<string, CalendarCell>;
}

export interface EntriesState {
  items: Entry[];
  filters: EntriesFilters;
  status: AsyncRequestStatus;
  deletingId: number | null;
  error: FriendlyError | null;
  importStatus: AsyncRequestStatus;
  lastFetchTime: number | null;
  stale: boolean;
  today: {
    date: string;
    rows: TodayRow[];
    status: AsyncRequestStatus;
    error: FriendlyError | null;
    dirty: Record<string, TodayRow>;
    savingStatus: AsyncRequestStatus;
    saveError: FriendlyError | null;
    lastFetchTime: number | null;
    stale: boolean;
  };
  stats: {
    snapshot: StatsSnapshot | null;
    status: AsyncRequestStatus;
    error: FriendlyError | null;
    date: string | null;
    lastFetchTime: number | null;
    stale: boolean;
  };
  finalizeStatus: AsyncRequestStatus;
  calendar: {
    startDate: string | null;
    endDate: string | null;
    days: string[];
    rows: CalendarRow[];
    status: AsyncRequestStatus;
    error: FriendlyError | null;
    saving: Record<string, boolean>;
    lastFetchTime: number | null;
  };
}

export interface ActivitiesState {
  all: Activity[];
  active: Activity[];
  status: AsyncRequestStatus;
  error: FriendlyError | null;
  mutationStatus: AsyncRequestStatus;
  mutationError: FriendlyError | null;
  selectedActivityId: number | null;
  lastFetchTime: number | null;
  stale: boolean;
}

export {};
