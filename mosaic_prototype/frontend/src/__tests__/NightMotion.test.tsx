import React, { type ReactElement } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import NightMotion from "../components/NightMotion";
import nightMotionReducer from "../store/nightMotionSlice";
import { getStreamProxyUrl } from "../api";

const notifyMock = jest.fn();
const fetchMock = jest.fn();
const createObjectURLMock = jest.fn(() => "blob:nightmotion-stream");
const revokeObjectURLMock = jest.fn();

const originalFetch = global.fetch;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

function createStore() {
  return configureStore({
    reducer: {
      nightMotion: nightMotionReducer,
    },
  });
}

function renderNightMotion() {
  const store = createStore();
  const ui: ReactElement = React.createElement(
    Provider,
    { store },
    React.createElement(NightMotion, { onNotify: notifyMock })
  );
  const utils = render(ui);
  return { store, ...utils };
}

describe("NightMotion component", () => {
  beforeAll(() => {
    Object.defineProperty(window.HTMLMediaElement.prototype, "load", {
      configurable: true,
      value: jest.fn(),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: jest.fn().mockResolvedValue(undefined),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: jest.fn(),
    });
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      writable: true,
      value: fetchMock as unknown as typeof fetch,
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createObjectURLMock,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeObjectURLMock,
    });
  });

  beforeEach(() => {
    notifyMock.mockReset();
    fetchMock.mockReset();
    createObjectURLMock.mockClear();
    revokeObjectURLMock.mockClear();
    const blob = new Blob(["mock"], { type: "image/jpeg" });
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => blob,
    } as unknown as Response);
    window.localStorage.clear();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  afterAll(() => {
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      writable: true,
      value: originalFetch,
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: originalRevokeObjectURL,
    });
  });

  it("renders credentials form and start button", () => {
    jest.useFakeTimers();
    renderNightMotion();
    act(() => {
      jest.advanceTimersByTime(60);
    });

    expect(screen.getByTestId("nightmotion-username")).toBeInTheDocument();
    expect(screen.getByTestId("nightmotion-password")).toBeInTheDocument();
    expect(screen.getByTestId("nightmotion-stream")).toBeInTheDocument();
    expect(screen.getByTestId("nightmotion-start")).toBeInTheDocument();
  });

  it("transitions from connecting to playing on start", async () => {
    jest.useFakeTimers();
    const { store } = renderNightMotion();
    act(() => {
      jest.advanceTimersByTime(60);
    });

    const username = "operator";
    const password = "secret";
    const streamUrl = "rtsp://camera/live";

    window.localStorage.setItem(
      "mosaic.auth",
      JSON.stringify({
        username,
        accessToken: "access-token",
        csrfToken: "csrf-token",
        tokenType: "Bearer",
        expiresAt: Date.now() + 60_000,
      })
    );

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    await user.type(screen.getByTestId("nightmotion-username"), username);
    await user.type(screen.getByTestId("nightmotion-password"), password);
    await user.type(screen.getByTestId("nightmotion-stream"), streamUrl);

    const startButton = screen.getByTestId("nightmotion-start");
    await user.click(startButton);

    await waitFor(() => expect(notifyMock).toHaveBeenCalledWith("Nastavení uloženo", "success"));
    expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/connecting/i);
    expect(store.getState().nightMotion.status).toBe("connecting");

    await act(async () => {
      jest.advanceTimersByTime(2050);
    });

    await act(async () => Promise.resolve());

    expect(store.getState().nightMotion.status).toBe("playing");
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("playing"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/live/i));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [requestedUrl, requestInit] = fetchMock.mock.calls[0];
    const expectedRequestUrl = getStreamProxyUrl(streamUrl, username, password);
    expect(requestedUrl).toBe(expectedRequestUrl);
    expect(requestInit).toMatchObject({
      headers: {
        Authorization: "Bearer access-token",
        "X-CSRF-Token": "csrf-token",
      },
    });
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);

    const videoElement = screen.getByTestId("nightmotion-video") as HTMLVideoElement;
    expect(videoElement.getAttribute("src")).toBe("blob:nightmotion-stream");
  });

  it("stops the stream and returns to idle", async () => {
    jest.useFakeTimers();
    const { store } = renderNightMotion();
    act(() => {
      jest.advanceTimersByTime(60);
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    await user.type(screen.getByTestId("nightmotion-username"), "operator");
    await user.type(screen.getByTestId("nightmotion-password"), "secret");
    await user.type(screen.getByTestId("nightmotion-stream"), "rtsp://camera/live");

    await user.click(screen.getByTestId("nightmotion-start"));

    await act(async () => {
      jest.advanceTimersByTime(2050);
    });
    await act(async () => Promise.resolve());
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("playing"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/live/i));

    const stopButton = screen.getByTestId("nightmotion-stop");
    expect(stopButton).not.toBeDisabled();
    await user.click(stopButton);

    await act(async () => {
      jest.advanceTimersByTime(60);
    });
    await act(async () => Promise.resolve());

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("idle"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/idle/i));
    const videoElement = screen.getByTestId("nightmotion-video") as HTMLVideoElement;
    expect(videoElement.getAttribute("src")).toBeNull();
    expect(revokeObjectURLMock).toHaveBeenCalled();
  });

  it("matches snapshot in idle state", () => {
    jest.useFakeTimers();
    const { asFragment } = renderNightMotion();

    act(() => {
      jest.advanceTimersByTime(60);
    });

    expect(asFragment()).toMatchSnapshot();
  });

  it("matches snapshot in playing state", async () => {
    jest.useFakeTimers();
    const { asFragment, store } = renderNightMotion();

    act(() => {
      jest.advanceTimersByTime(60);
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    await user.type(screen.getByTestId("nightmotion-username"), "operator");
    await user.type(screen.getByTestId("nightmotion-password"), "secret");
    await user.type(screen.getByTestId("nightmotion-stream"), "rtsp://camera/live");
    await user.click(screen.getByTestId("nightmotion-start"));

    await act(async () => {
      jest.advanceTimersByTime(2050);
    });
    await act(async () => Promise.resolve());

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("playing"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/live/i));

    expect(asFragment()).toMatchSnapshot();
  });
});
