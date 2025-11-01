import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { AppThunk, RootState } from "./index";

export type NightMotionStatus = "idle" | "connecting" | "playing" | "error";

export interface NightMotionState {
  username: string;
  password: string;
  streamUrl: string;
  status: NightMotionStatus;
  error: string | null;
}

export const initialState: NightMotionState = {
  username: "",
  password: "",
  streamUrl: "",
  status: "idle",
  error: null,
};

type NightMotionField = Exclude<keyof NightMotionState, "status" | "error">;

const nightMotionSlice = createSlice({
  name: "nightMotion",
  initialState,
  reducers: {
    setField: (
      state,
      action: PayloadAction<{
        field: NightMotionField;
        value: string;
      }>
    ) => {
      const { field, value } = action.payload;
      state[field] = value;
    },
    setStatus: (state, action: PayloadAction<NightMotionStatus>) => {
      state.status = action.payload;
      if (action.payload !== "error") {
        state.error = null;
      }
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    resetState: () => initialState,
  },
});

export const { setField, setStatus, setError, resetState } = nightMotionSlice.actions;

export const startStream = (): AppThunk<Promise<void>> => async (dispatch, getState) => {
  const { nightMotion } = getState();
  if (nightMotion.status === "connecting" || nightMotion.status === "playing") {
    return;
  }

  dispatch(setError(null));
  dispatch(setStatus("connecting"));

  await new Promise((resolve) => {
    setTimeout(resolve, 2000);
  });

  dispatch(setStatus("playing"));
};

export const stopStream = (): AppThunk => (dispatch, getState) => {
  const { nightMotion } = getState();
  if (nightMotion.status === "idle") {
    return;
  }
  dispatch(setError(null));
  dispatch(setStatus("idle"));
};

export const selectNightMotionState = (state: RootState): NightMotionState => state.nightMotion;

export default nightMotionSlice.reducer;
