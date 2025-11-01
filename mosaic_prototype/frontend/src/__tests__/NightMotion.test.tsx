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

const textEncoder = new TextEncoder();
const sampleFrame = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);

function buildMJPEGChunks(frames: Uint8Array[]): Uint8Array[] {
  const chunks: Uint8Array[] = [];
  frames.forEach((frameBytes) => {
    const header = textEncoder.encode(
      `--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${frameBytes.length}\r\n\r\n`
    );
    const footer = textEncoder.encode("\r\n");
    chunks.push(header);
    chunks.push(frameBytes);
    chunks.push(footer);
  });
  chunks.push(textEncoder.encode("--frame--\r\n"));
  return chunks;
}

function setupStream(frames: Uint8Array[]) {
  const chunks = buildMJPEGChunks(frames);
  let index = 0;

  const read = jest.fn(async () => {
    if (index < chunks.length) {
      const chunk = chunks[index];
      index += 1;
      return { value: chunk, done: false };
    }
    return { value: undefined, done: true };
  });

  fetchMock.mockResolvedValueOnce({
    ok: true,
    body: {
      getReader: () => ({ read }),
    },
  } as unknown as Response);

  return { read };
}

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
    Object.defineProperty(window.HTMLImageElement.prototype, "decode", {
      configurable: true,
      value: jest.fn().mockResolvedValue(undefined),
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
    fetchMock.mockImplementation(() => Promise.reject(new Error("Unexpected fetch call")));
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

  it("transitions from starting to active on start", async () => {
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

    setupStream([sampleFrame]);
    const startButton = screen.getByTestId("nightmotion-start");

    await user.click(startButton);

    await waitFor(() => expect(notifyMock).toHaveBeenCalledWith("Nastavení uloženo", "success"));
    expect(store.getState().nightMotion.status).toBe("starting");
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

    await waitFor(() => expect(createObjectURLMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));

    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    expect(streamImage).toHaveAttribute("src", "blob:nightmotion-stream");
    expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/active/i);
    expect(revokeObjectURLMock).not.toHaveBeenCalled();
  });

  it("stops the stream and returns to idle", async () => {
    jest.useFakeTimers();
    const { store } = renderNightMotion();
    act(() => {
      jest.advanceTimersByTime(60);
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    window.localStorage.setItem(
      "mosaic.auth",
      JSON.stringify({
        username: "operator",
        accessToken: "access-token",
        csrfToken: "csrf-token",
        tokenType: "Bearer",
        expiresAt: Date.now() + 60_000,
      })
    );

    await user.type(screen.getByTestId("nightmotion-username"), "operator");
    await user.type(screen.getByTestId("nightmotion-password"), "secret");
    await user.type(screen.getByTestId("nightmotion-stream"), "rtsp://camera/live");

    setupStream([sampleFrame]);
    await user.click(screen.getByTestId("nightmotion-start"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(createObjectURLMock).toHaveBeenCalled());
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));
    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    expect(streamImage).toHaveAttribute("src", "blob:nightmotion-stream");

    const stopButton = screen.getByTestId("nightmotion-stop");
    expect(stopButton).not.toBeDisabled();
    await user.click(stopButton);

    await act(async () => {
      jest.advanceTimersByTime(60);
    });
    await act(async () => Promise.resolve());

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("idle"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/idle/i));
    expect(screen.queryByTestId("nightmotion-stream-img")).not.toBeInTheDocument();
    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:nightmotion-stream");
  });

  it("matches snapshot in idle state", () => {
    jest.useFakeTimers();
    const { asFragment } = renderNightMotion();

    act(() => {
      jest.advanceTimersByTime(60);
    });

    expect(asFragment()).toMatchSnapshot();
  });

  it("matches snapshot in active state", async () => {
    jest.useFakeTimers();
    const { asFragment, store } = renderNightMotion();

    act(() => {
      jest.advanceTimersByTime(60);
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    window.localStorage.setItem(
      "mosaic.auth",
      JSON.stringify({
        username: "operator",
        accessToken: "access-token",
        csrfToken: "csrf-token",
        tokenType: "Bearer",
        expiresAt: Date.now() + 60_000,
      })
    );

    await user.type(screen.getByTestId("nightmotion-username"), "operator");
    await user.type(screen.getByTestId("nightmotion-password"), "secret");
    await user.type(screen.getByTestId("nightmotion-stream"), "rtsp://camera/live");

    setupStream([sampleFrame]);
    await user.click(screen.getByTestId("nightmotion-start"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(createObjectURLMock).toHaveBeenCalled());
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/active/i));

    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    expect(streamImage).toHaveAttribute("src", "blob:nightmotion-stream");

    expect(asFragment()).toMatchSnapshot();
  });
});
