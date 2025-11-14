import { submitOfflineMutation, drainPendingWrites, getPendingCount } from "../offline/queue";
import { clearPendingWrites } from "../offline/db";

jest.mock("../apiClient", () => ({
  __esModule: true,
  default: {
    request: jest.fn(),
  },
}));

const apiClient = require("../apiClient").default as { request: jest.Mock };

function setNavigatorOnline(value: boolean) {
  Object.defineProperty(window.navigator, "onLine", {
    value,
    configurable: true,
  });
}

describe("offline queue", () => {
  beforeEach(async () => {
    apiClient.request.mockReset();
    setNavigatorOnline(true);
    await clearPendingWrites();
  });

  it("queues mutations when offline", async () => {
    setNavigatorOnline(false);
    const result = await submitOfflineMutation({
      action: "add_entry",
      endpoint: "/add_entry",
      method: "POST",
      payload: { sample: "data" },
    });
    expect(result.queued).toBe(true);
    expect(apiClient.request).not.toHaveBeenCalled();
    expect(await getPendingCount()).toBe(1);
  });

  it("flushes queued writes when connection is restored", async () => {
    setNavigatorOnline(false);
    await submitOfflineMutation({
      action: "add_entry",
      endpoint: "/add_entry",
      method: "POST",
      payload: { value: 1 },
    });
    expect(await getPendingCount()).toBe(1);

    setNavigatorOnline(true);
    apiClient.request.mockResolvedValueOnce({ data: { ok: true } });
    await drainPendingWrites();
    expect(apiClient.request).toHaveBeenCalledTimes(1);
    expect(await getPendingCount()).toBe(0);
  });

  it("retries conflicts with overwrite flag", async () => {
    setNavigatorOnline(false);
    await submitOfflineMutation({
      action: "add_activity",
      endpoint: "/add_activity",
      method: "POST",
      payload: { name: "Offline", category: "Test", goal: 1 },
    });
    setNavigatorOnline(true);

    apiClient.request
      .mockRejectedValueOnce({ response: { status: 409 } })
      .mockResolvedValueOnce({ data: { message: "ok" } });

    await drainPendingWrites();

    expect(apiClient.request).toHaveBeenCalledTimes(2);
    expect(apiClient.request).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Overwrite-Existing": "1",
        }),
      })
    );
    expect(await getPendingCount()).toBe(0);
  });
});
