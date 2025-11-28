import React from "react";
import { render, screen } from "@testing-library/react";
import SkeletonTable from "../components/SkeletonTable";

describe("SkeletonTable", () => {
  it("renders correct number of skeleton rows", () => {
    const { container } = render(<SkeletonTable rows={3} columns={4} />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(3);
  });

  it("renders correct number of skeleton columns", () => {
    const { container } = render(<SkeletonTable rows={2} columns={5} />);
    const firstRow = container.querySelector("tbody tr");
    const cells = firstRow?.querySelectorAll("td");
    expect(cells).toHaveLength(5);
  });

  it("applies shimmer animation styles by checking keyframes exist", () => {
    render(<SkeletonTable rows={1} columns={1} />);
    const shimmerStyle = document.getElementById("skeleton-shimmer-keyframes");
    expect(shimmerStyle).toBeInTheDocument();
    expect(shimmerStyle?.textContent).toContain("@keyframes shimmer");
  });

  it("renders with default props", () => {
    const { container } = render(<SkeletonTable />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(3); // Default rows
    
    const firstRow = rows[0];
    const cells = firstRow.querySelectorAll("td");
    expect(cells).toHaveLength(5); // Default columns (changed from 4 to 5)
  });
});
