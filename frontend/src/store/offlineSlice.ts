import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "./index";

interface OfflineState {
  online: boolean;
  syncing: boolean;
  pendingCount: number;
  lastSyncAt: string | null;
}

const initialState: OfflineState = {
  online: typeof navigator === "undefined" ? true : navigator.onLine,
  syncing: false,
  pendingCount: 0,
  lastSyncAt: null,
};

const offlineSlice = createSlice({
  name: "offline",
  initialState,
  reducers: {
    setOnlineStatus(state, action: PayloadAction<boolean>) {
      state.online = action.payload;
    },
    setSyncing(state, action: PayloadAction<boolean>) {
      state.syncing = action.payload;
    },
    setPendingCount(state, action: PayloadAction<number>) {
      state.pendingCount = action.payload;
    },
    setLastSyncAt(state, action: PayloadAction<string | null>) {
      state.lastSyncAt = action.payload;
    },
  },
});

export const { setOnlineStatus, setSyncing, setPendingCount, setLastSyncAt } = offlineSlice.actions;

export const selectOfflineState = (state: RootState) => state.offline;

export default offlineSlice.reducer;
