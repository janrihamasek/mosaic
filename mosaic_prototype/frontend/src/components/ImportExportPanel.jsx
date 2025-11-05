import React, { useCallback, useMemo, useState } from "react";
import { styles } from "../styles/common";
import { useCompactLayout } from "../utils/useBreakpoints";
import { formatError } from "../utils/errors";
import { downloadCsvExport, downloadJsonExport } from "../api";
import CsvImportButton from "./CsvImportButton";

export default function ImportExportPanel({ onNotify }) {
  const { isCompact } = useCompactLayout();
  const [exportingFormat, setExportingFormat] = useState(null);

  const containerStyle = useMemo(
    () => ({
      ...styles.card,
      margin: 0,
      display: "flex",
      flexDirection: isCompact ? "column" : "row",
      gap: "0.75rem",
      alignItems: isCompact ? "stretch" : "center",
      justifyContent: "space-between",
    }),
    [isCompact]
  );

  const actionRowStyle = useMemo(
    () => ({
      display: "flex",
      flexWrap: "wrap",
      gap: "0.75rem",
      justifyContent: isCompact ? "stretch" : "flex-end",
    }),
    [isCompact]
  );

  const isExporting = exportingFormat !== null;

  const handleExport = useCallback(
    async (format) => {
      if (exportingFormat) return;
      setExportingFormat(format);
      const exportFn = format === "json" ? downloadJsonExport : downloadCsvExport;
      try {
        const result = await exportFn();
        const { blob, filename } = result;
        if (typeof window === "undefined" || !blob) {
          throw new Error("Export is not supported in this environment");
        }
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filename || `mosaic-export.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
        onNotify?.(`Exported ${format.toUpperCase()} file`, "success");
      } catch (err) {
        onNotify?.(`Failed to export data: ${formatError(err)}`, "error");
      } finally {
        setExportingFormat(null);
      }
    },
    [exportingFormat, onNotify]
  );

  return (
    <div style={containerStyle}>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Entries data tools</h3>
        <span style={{ ...styles.textMuted, fontSize: "0.85rem" }}>
          Import or export entries for reporting and backups.
        </span>
      </div>
      <div style={actionRowStyle}>
        <CsvImportButton onNotify={onNotify} variant="import" />
        <button
          type="button"
          onClick={() => handleExport("csv")}
          style={{
            ...styles.button,
            opacity: exportingFormat === "csv" ? 0.7 : 1,
          }}
          disabled={isExporting}
        >
          {exportingFormat === "csv" ? "Exporting CSV…" : "Export CSV"}
        </button>
        <button
          type="button"
          onClick={() => handleExport("json")}
          style={{
            ...styles.button,
            backgroundColor: "#2f9e44",
            opacity: exportingFormat === "json" ? 0.7 : 1,
          }}
          disabled={isExporting}
        >
          {exportingFormat === "json" ? "Exporting JSON…" : "Export JSON"}
        </button>
      </div>
    </div>
  );
}
