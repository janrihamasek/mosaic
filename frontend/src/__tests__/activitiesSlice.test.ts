import { AnyAction, configureStore } from "@reduxjs/toolkit";
import activitiesReducer, { batchUpdateActivities } from "../store/activitiesSlice";
import entriesReducer from "../store/entriesSlice";
import * as api from "../api";
import * as offlineQueue from "../offline/queue";

jest.mock("../api", () => ({
  batchActivities: jest.fn(),
  fetchActivities: jest.fn(),
}));

jest.mock("../offline/queue", () => ({
  submitOfflineMutation: jest.fn(),
  isOfflineError: jest.fn(),
}));

const mockedBatchActivities = api.batchActivities as unknown as jest.Mock;
const mockedIsOfflineError = offlineQueue.isOfflineError as unknown as jest.Mock;
const mockedSubmitOffline = offlineQueue.submitOfflineMutation as unknown as jest.Mock;

const baseStore = () =>
  configureStore({
    reducer: {
      activities: activitiesReducer,
      entries: entriesReducer,
    },
  });

describe("activitiesSlice batchUpdateActivities", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedIsOfflineError.mockReturnValue(false);
  });

  it("dispatches batchActivities and fulfills with processed ids", async () => {
    mockedBatchActivities.mockResolvedValue({ processed: [1, 2], skipped: [] });
    const store = baseStore();

    const action = batchUpdateActivities({ action: "activate", ids: [1, 2] }) as unknown as AnyAction;
    const result = await store.dispatch(action);

    expect(mockedBatchActivities).toHaveBeenCalledWith({ action: "activate", ids: [1, 2] });
    expect(result.type).toContain("fulfilled");
    expect(result.payload.processed).toEqual([1, 2]);
    expect(mockedSubmitOffline).not.toHaveBeenCalled();
  });

  it("falls back to offline queue when offline error occurs", async () => {
    const error = new Error("offline");
    mockedBatchActivities.mockRejectedValue(error);
    mockedIsOfflineError.mockReturnValue(true);
    mockedSubmitOffline.mockResolvedValue({ queued: true });
    const store = baseStore();

    const action = batchUpdateActivities({ action: "deactivate", ids: [3] }) as unknown as AnyAction;
    const result = await store.dispatch(action);

    expect(mockedIsOfflineError).toHaveBeenCalled();
    expect(mockedSubmitOffline).toHaveBeenCalledWith({
      action: "activities_batch",
      endpoint: "/activities/batch",
      method: "POST",
      payload: { action: "deactivate", ids: [3] },
    });
    expect(result.type).toContain("fulfilled");
  });
});
