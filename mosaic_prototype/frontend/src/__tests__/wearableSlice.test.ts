import wearableReducer, {
  fetchWearableDay,
  fetchWearableTrends,
  resetWearableState,
} from "../store/wearableSlice";

describe("wearableSlice", () => {
  it("sets loading state when fetching day data", () => {
    const state = wearableReducer(undefined, fetchWearableDay.pending("requestId"));
    expect(state.status).toBe("loading");
    expect(state.error).toBeNull();
  });

  it("populates day data when fulfilled", () => {
    const payload = { steps: 1234 };
    const state = wearableReducer(undefined, fetchWearableDay.fulfilled(payload, "req", undefined));
    expect(state.status).toBe("succeeded");
    expect(state.day).toEqual(payload);
  });

  it("records error on failed trends", () => {
    const state = wearableReducer(undefined, fetchWearableTrends.rejected(new Error("oops"), "req", undefined));
    expect(state.status).toBe("failed");
    expect(state.error).toBe("oops");
  });

  it("resets to initial state", () => {
    const dirtyState = {
      day: { steps: 10 },
      trends: { heart: [] },
      status: "succeeded" as const,
      error: "boom",
    };
    const state = wearableReducer(dirtyState, resetWearableState());
    expect(state).toEqual({
      day: null,
      trends: {},
      status: "idle",
      error: null,
    });
  });
});
