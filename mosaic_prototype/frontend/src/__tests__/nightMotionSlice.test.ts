import reducer, {
  initialState,
  setError,
  setStatus,
  type NightMotionState,
} from "../store/nightMotionSlice";

describe("nightMotionSlice reducers", () => {
  it("updates status via setStatus", () => {
    const next = reducer(initialState, setStatus("connecting"));
    expect(next.status).toBe("connecting");
    expect(next.error).toBeNull();
  });

  it("clears error when status transitions away from error", () => {
    const erroredState: NightMotionState = {
      ...initialState,
      status: "error",
      error: "Stream nelze navázat",
    };
    const next = reducer(erroredState, setStatus("playing"));
    expect(next.status).toBe("playing");
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
