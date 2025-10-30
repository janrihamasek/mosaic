import React, { useMemo } from "react";
import { styles } from "../../styles/common";
import { useCompactLayout } from "../../utils/useBreakpoints";

const resolveCellValue = (row, column) => {
  if (typeof column.render === "function") {
    return column.render(row);
  }
  if (column.key && Object.prototype.hasOwnProperty.call(row, column.key)) {
    return row[column.key];
  }
  return "";
};

const getColumnKey = (column, index) => column.key ?? `column-${index}`;

export default function DataTable({
  columns = [],
  data = [],
  isLoading = false,
  error,
  onRowClick,
  emptyMessage = "No records to display.",
  loadingMessage = "Loading…",
  errorLabel = "Unable to load records.",
}) {
  const { isCompact } = useCompactLayout();
  const hasData = Array.isArray(data) && data.length > 0;
  const columnMeta = useMemo(
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

  const renderStateMessage = (message, tone = "info") => {
    if (React.isValidElement(message)) {
      return message;
    }
    const toneStyle =
      tone === "error"
        ? { color: "#f28b82" }
        : tone === "muted"
        ? { color: "#9ba3af", fontStyle: "italic" }
        : {};

    return (
      <div style={{ ...styles.loadingText, ...toneStyle, marginTop: 0 }}>
        {message}
      </div>
    );
  };

  if (isLoading) {
    return renderStateMessage(loadingMessage);
  }

  if (error) {
    const errorMessage =
      typeof error === "string"
        ? error
        : error?.friendlyMessage || error?.message || errorLabel;
    return renderStateMessage(errorMessage, "error");
  }

  if (!hasData) {
    return renderStateMessage(emptyMessage, "muted");
  }

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
            style={{ ...styles.tableRow, ...baseRowStyle }}
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
}
