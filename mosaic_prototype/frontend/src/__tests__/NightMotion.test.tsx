import React, { type ReactElement } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import NightMotion from "../components/NightMotion";
import nightMotionReducer from "../store/nightMotionSlice";
import { getStreamProxyUrl } from "../api";

const notifyMock = jest.fn();

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
  });

  beforeEach(() => {
    notifyMock.mockReset();
    window.localStorage.clear();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
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

    const startButton = screen.getByTestId("nightmotion-start");
    await user.click(startButton);

    await waitFor(() => expect(notifyMock).toHaveBeenCalledWith("Nastavení uloženo", "success"));
    expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/starting/i);
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("starting"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/starting/i));

    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    const parsedUrl = new URL(streamImage.getAttribute("src") ?? "");
    const expectedRequestUrl = new URL(getStreamProxyUrl(streamUrl, username, password));
    expect(parsedUrl.origin + parsedUrl.pathname).toBe(expectedRequestUrl.origin + expectedRequestUrl.pathname);
    expect(parsedUrl.searchParams.get("url")).toBe(expectedRequestUrl.searchParams.get("url"));
    expect(parsedUrl.searchParams.get("username")).toBe(expectedRequestUrl.searchParams.get("username"));
    expect(parsedUrl.searchParams.get("password")).toBe(expectedRequestUrl.searchParams.get("password"));
    expect(parsedUrl.searchParams.get("token")).toBe("access-token");
    expect(parsedUrl.searchParams.get("csrf")).toBe("csrf-token");

    act(() => {
      fireEvent.load(streamImage);
    });

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/active/i));
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

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("starting"));
    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    act(() => {
      fireEvent.load(streamImage);
    });
    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/active/i));

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

    await user.type(screen.getByTestId("nightmotion-username"), "operator");
    await user.type(screen.getByTestId("nightmotion-password"), "secret");
    await user.type(screen.getByTestId("nightmotion-stream"), "rtsp://camera/live");
    await user.click(screen.getByTestId("nightmotion-start"));

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("starting"));
    const streamImage = await screen.findByTestId("nightmotion-stream-img");
    act(() => {
      fireEvent.load(streamImage);
    });

    await waitFor(() => expect(store.getState().nightMotion.status).toBe("active"));
    await waitFor(() => expect(screen.getByTestId("nightmotion-status")).toHaveTextContent(/active/i));

    expect(asFragment()).toMatchSnapshot();
  });
});
