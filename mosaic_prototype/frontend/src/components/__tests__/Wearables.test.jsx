import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";

import Wearables from "../Wearables";
import { store } from "../../store";
import { resetWearableState } from "../../store/wearableSlice";

jest.mock("../../api", () => ({
  fetchWearableDay: jest.fn(),
  fetchWearableTrends: jest.fn(),
}));

const { fetchWearableDay, fetchWearableTrends } = require("../../api");

const buildTrendResponse = (metric, window) => ({
  metric,
  window,
  average: 10,
  values: Array.from({ length: window }, (_, index) => ({
    date: `2025-11-${String(index + 1).padStart(2, "0")}`,
    value: index + 1,
  })),
});

beforeEach(() => {
  jest.clearAllMocks();
  store.dispatch(resetWearableState());
  fetchWearableDay.mockResolvedValue({
    date: "2025-11-12",
    steps: 1500,
    sleep: { total_min: 80, sessions: 1, efficiency: 85 },
    hr: { rest: 60, avg: 70, min: 55, max: 90 },
  });
  fetchWearableTrends.mockImplementation(({ metric, window }) =>
    Promise.resolve(buildTrendResponse(metric, window))
  );
});

function renderComponent() {
  return render(
    <Provider store={store}>
      <Wearables />
    </Provider>
  );
}

test("renders wearable summary and refreshes data", async () => {
  renderComponent();

  await waitFor(() => expect(fetchWearableDay).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(fetchWearableTrends).toHaveBeenCalledTimes(6));

  expect(screen.getByText(/Wearable Insights/i)).toBeInTheDocument();
  expect(screen.getByText("1,500")).toBeInTheDocument();
  expect(screen.getByText("60")).toBeInTheDocument();
  expect(screen.getByText("80")).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: /refresh/i });
  fireEvent.click(refreshButton);

  await waitFor(() => expect(fetchWearableDay).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(fetchWearableTrends).toHaveBeenCalledTimes(12));
});
