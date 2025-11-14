import reducer, {
  initialState,
  setError,
  setStatus,
  type NightMotionState,
} from "../store/nightMotionSlice";

describe("nightMotionSlice reducers", () => {
  it("updates status via setStatus", () => {
    const next = reducer(initialState, setStatus("starting"));
    expect(next.status).toBe("starting");
    expect(next.error).toBeNull();
  });

  it("clears error when status transitions away from error", () => {
    const erroredState: NightMotionState = {
      ...initialState,
      status: "error",
      error: "Stream nelze navázat",
    };
    const next = reducer(erroredState, setStatus("active"));
    expect(next.status).toBe("active");
    expect(next.error).toBeNull();
  });

  it("keeps error when status stays on error", () => {
    const erroredState: NightMotionState = {
      ...initialState,
      status: "error",
      error: "Stream nelze navázat",
    };
    const next = reducer(erroredState, setStatus("error"));
    expect(next.status).toBe("error");
    expect(next.error).toBe("Stream nelze navázat");
  });

  it("allows error to be set explicitly", () => {
    const next = reducer(initialState, setError("Missing credentials"));
    expect(next.error).toBe("Missing credentials");
  });
});
