import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ImportExportPanel from "../ImportExportPanel";

jest.mock("react-redux", () => ({
  useDispatch: () => jest.fn(() => Promise.resolve({ unwrap: () => Promise.resolve() })),
}));

const mockDownloadCsvExport = jest.fn(() =>
  Promise.resolve({ blob: new Blob(["csv"]), filename: "test.csv" })
);
const mockDownloadJsonExport = jest.fn(() =>
  Promise.resolve({ blob: new Blob(['{"a":1}']), filename: "test.json" })
);

jest.mock("../../api", () => ({
  downloadCsvExport: (...args) => mockDownloadCsvExport(...args),
  downloadJsonExport: (...args) => mockDownloadJsonExport(...args),
}));

describe("ImportExportPanel", () => {
  beforeEach(() => {
    mockDownloadCsvExport.mockClear();
    mockDownloadJsonExport.mockClear();
    // jsdom helpers for download link
    global.URL.createObjectURL = jest.fn(() => "blob:url");
    global.URL.revokeObjectURL = jest.fn();
  });

  it("triggers CSV and JSON export", async () => {
    render(<ImportExportPanel onNotify={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: /export csv/i }));
    expect(mockDownloadCsvExport).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: /export json/i }));
    expect(mockDownloadJsonExport).toHaveBeenCalledTimes(1);
  });
});
