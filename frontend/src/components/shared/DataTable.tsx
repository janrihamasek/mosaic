import React, { useMemo } from "react";
import type { CSSProperties } from "react";

import ErrorState from "../ErrorState";
import Loading from "../Loading";
import { styles } from "../../styles/common";
import { useCompactLayout } from "../../utils/useBreakpoints";
import type { DataTableColumn, DataTableProps } from "../../types/props";

interface ColumnMeta extends DataTableColumn {
  _id: string;
  label: string;
}

const resolveCellValue = (row: Record<string, unknown>, column: DataTableColumn) => {
  if (typeof column.render === "function") {
    return column.render(row);
  }
  if (column.key && Object.prototype.hasOwnProperty.call(row, column.key)) {
    return (row as Record<string, unknown>)[column.key];
  }
  return "";
};

const getColumnKey = (column: DataTableColumn, index: number) => column.key ?? `column-${index}`;

const DataTable: React.FC<DataTableProps> = ({
  columns = [],
  data = [],
  isLoading = false,
  error,
  onRowClick,
  emptyMessage = "No records to display.",
  loadingMessage = "Loading…",
  errorLabel = "Unable to load records.",
  rowStyle,
}) => {
  const { isCompact } = useCompactLayout();
  const hasData = Array.isArray(data) && data.length > 0;
  const columnMeta = useMemo<ColumnMeta[]>(
    () =>
      columns.map((column, index) => ({
        ...column,
        _id: getColumnKey(column, index),
        label: column.label ?? column.title ?? column.key ?? `Column ${index + 1}`,
      })),
    [columns]
  );

  const baseRowStyle = {
    cursor: typeof onRowClick === "function" ? "pointer" : "default",
  };

  if (isLoading) {
    return <Loading message={loadingMessage} />;
  }

  if (error) {
    const errorMessage =
      typeof error === "string"
        ? error
        : error?.friendlyMessage || error?.message || errorLabel;
    return <ErrorState message={errorMessage ?? errorLabel} />;
  }

  if (!hasData) {
    return (
      <div style={{ ...styles.loadingText, color: "#9ba3af", fontStyle: "italic", marginTop: 0 }}>
        {emptyMessage}
      </div>
    );
  }

  const resolveRowStyle = (row: Record<string, unknown>): CSSProperties | undefined =>
    typeof rowStyle === "function" ? rowStyle(row) : undefined;

  if (isCompact) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {data.map((row, rowIndex) => (
          <div
            key={row.id ?? rowIndex}
            style={{
              ...styles.card,
              margin: 0,
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              ...baseRowStyle,
              ...(resolveRowStyle(row) ?? {}),
            }}
            onClick={() => onRowClick?.(row)}
            role={onRowClick ? "button" : undefined}
            tabIndex={onRowClick ? 0 : undefined}
            onKeyDown={(event) => {
              if (!onRowClick) return;
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onRowClick(row);
              }
            }}
          >
            {columnMeta.map((column) => (
              <div
                key={column._id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.25rem",
                }}
              >
                <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>
                  {column.label}
                </span>
                <div style={{ fontSize: "0.95rem" }}>
                  {resolveCellValue(row, column)}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <table style={styles.table}>
      <thead>
        <tr style={styles.tableHeader}>
          {columnMeta.map((column) => (
            <th key={column._id} style={{ width: column.width }}>
              {column.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, rowIndex) => (
          <tr
            key={row.id ?? rowIndex}
            style={{ ...styles.tableRow, ...baseRowStyle, ...(resolveRowStyle(row) ?? {}) }}
            onClick={() => onRowClick?.(row)}
          >
            {columnMeta.map((column) => (
              <td key={column._id} style={{ width: column.width }}>
                {resolveCellValue(row, column)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default DataTable;
