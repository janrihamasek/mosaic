import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useDispatch, useSelector } from "react-redux";

import ActivityForm from "../ActivityForm";
import { createActivity } from "../../store/activitiesSlice";

jest.mock("react-redux", () => {
  const actual = jest.requireActual("react-redux");
  return {
    ...actual,
    useDispatch: jest.fn(),
    useSelector: jest.fn(),
  };
});

jest.mock("../../store/activitiesSlice", () => {
  const actual = jest.requireActual("../../store/activitiesSlice");
  return {
    ...actual,
    createActivity: jest.fn((payload) => () => {
      const resolved = Promise.resolve({ ok: true, payload });
      resolved.unwrap = () => Promise.resolve({ ok: true, payload });
      return resolved;
    }),
  };
});

const mockedDispatch = jest.fn(() => {
  const resolved = Promise.resolve({ ok: true });
  resolved.unwrap = () => Promise.resolve({ ok: true });
  return resolved;
});

beforeEach(() => {
  jest.clearAllMocks();
  mockedDispatch.mockClear();
  useDispatch.mockReturnValue(mockedDispatch);
  useSelector.mockImplementation((selector) =>
    selector({
      activities: {
        all: [],
        active: [],
        status: "idle",
        error: null,
        mutationStatus: "idle",
        mutationError: null,
        selectedActivityId: null,
      },
    })
  );
});

afterEach(() => {
  useSelector.mockReset();
});

const expandForm = () => {
  fireEvent.click(screen.getByRole("button", { name: /create activity/i }));
};

test("hides goal selectors when activity type is negative", () => {
  render(<ActivityForm />);
  expandForm();

  fireEvent.change(screen.getByLabelText(/Activity type/i), { target: { value: "negative" } });

  expect(screen.queryByText(/Per day/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Negative activities do not track a goal/i)).toBeInTheDocument();
});

test("submits goal zero payload for negative activities", async () => {
  render(<ActivityForm />);
  expandForm();

  fireEvent.change(screen.getByPlaceholderText("Activity"), { target: { value: "Digital Detox" } });
  fireEvent.change(screen.getByPlaceholderText("Category"), { target: { value: "Mindfulness" } });
  fireEvent.change(screen.getByLabelText(/Activity type/i), { target: { value: "negative" } });
  fireEvent.change(screen.getByPlaceholderText("Description (optional)"), {
    target: { value: "Reset every evening" },
  });

  fireEvent.click(screen.getByRole("button", { name: /enter/i }));

  await waitFor(() => expect(createActivity).toHaveBeenCalled());

  const payload = createActivity.mock.calls[0][0];
  expect(payload).toMatchObject({
    name: "Digital Detox",
    category: "Mindfulness",
    activity_type: "negative",
    goal: 0,
  });
  expect(payload.frequency_per_day).toBe(1);
  expect(payload.frequency_per_week).toBe(1);
});
