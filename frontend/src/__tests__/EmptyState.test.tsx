import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import EmptyState from "../components/EmptyState";

describe("EmptyState", () => {
  it("renders message text", () => {
    render(<EmptyState message="No data available" />);
    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("renders hint text when provided", () => {
    render(
      <EmptyState 
        message="No records found" 
        hint="Try adding some data first" 
      />
    );
    expect(screen.getByText("Try adding some data first")).toBeInTheDocument();
  });

  it("renders action button when provided", () => {
    const mockOnClick = jest.fn();
    render(
      <EmptyState 
        message="No activities" 
        action={{ label: "Add activity", onClick: mockOnClick }} 
      />
    );
    
    const button = screen.getByRole("button", { name: "Add activity" });
    expect(button).toBeInTheDocument();
  });

  it("calls action onClick when button is clicked", () => {
    const mockOnClick = jest.fn();
    render(
      <EmptyState 
        message="No activities" 
        action={{ label: "Add activity", onClick: mockOnClick }} 
      />
    );
    
    const button = screen.getByRole("button", { name: "Add activity" });
    fireEvent.click(button);
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it("renders without action button when not provided", () => {
    render(<EmptyState message="No data" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders without hint when not provided", () => {
    render(<EmptyState message="No data" />);
    // Message should be present
    expect(screen.getByText("No data")).toBeInTheDocument();
    // Hint should not be present (checking for a common hint pattern)
    expect(screen.queryByText(/try/i)).not.toBeInTheDocument();
  });
});
