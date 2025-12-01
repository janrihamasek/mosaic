import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { render, screen, fireEvent } from "@testing-library/react";
import ActivityDetail from "../components/ActivityDetail";

const renderWithStore = (ui: React.ReactElement) => {
  const store = configureStore({
    reducer: () => ({}),
  });
  return render(<Provider store={store}>{ui}</Provider>);
};

describe("ActivityDetail validation", () => {
  it("disables Save when category is empty and enables after input", () => {
    const activity = {
      id: 1,
      name: "Test Activity",
      category: "",
      description: "",
      activity_type: "positive",
      frequency_per_day: 1,
      frequency_per_week: 1,
      goal: 1,
    };

    renderWithStore(
      <ActivityDetail activity={activity} onClose={() => {}} onNotify={() => {}} />
    );

    const saveButton = screen.getByRole("button", { name: /save/i });
    expect(saveButton).toBeDisabled();

    const categoryInput = screen.getByLabelText(/category/i);
    fireEvent.change(categoryInput, { target: { value: "Health" } });

    expect(saveButton).not.toBeDisabled();
  });
});
