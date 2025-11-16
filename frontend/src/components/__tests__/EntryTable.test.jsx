import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";

import EntryTable from "../EntryTable";
import entriesReducer from "../../store/entriesSlice";
import { styles } from "../../styles/common";

const buildEntriesState = (items) => ({
  items,
  filters: { startDate: null, endDate: null, activity: "all", category: "all" },
  status: "idle",
  deletingId: null,
  error: null,
  importStatus: "idle",
  today: {
    date: "2024-01-01",
    rows: [],
    status: "idle",
    error: null,
    dirty: {},
    savingStatus: "idle",
    saveError: null,
  },
  stats: {
    snapshot: null,
    status: "idle",
    error: null,
    date: null,
  },
  finalizeStatus: "idle",
});

const renderWithEntries = (entries) => {
  const store = configureStore({
    reducer: {
      entries: entriesReducer,
    },
    preloadedState: {
      entries: buildEntriesState(entries),
    },
  });
  return render(
    <Provider store={store}>
      <EntryTable />
    </Provider>
  );
};

test("colors entry rows by activity type", () => {
  renderWithEntries([
    {
      id: 1,
      date: "2024-01-01",
      activity: "Positive Habit",
      value: 1,
      category: "Health",
      goal: 1,
      activity_type: "positive",
    },
    {
      id: 2,
      date: "2024-01-01",
      activity: "Negative Habit",
      value: 0,
      category: "Health",
      goal: 0,
      activity_type: "negative",
    },
  ]);

  const positiveRow = screen.getByText("Positive Habit").closest("tr");
  expect(positiveRow).toHaveStyle(`background-color: ${styles.positiveRow.backgroundColor}`);

  const negativeRow = screen.getByText("Negative Habit").closest("tr");
  expect(negativeRow).toHaveStyle(`background-color: ${styles.negativeRow.backgroundColor}`);
});
