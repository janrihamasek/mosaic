import React, { useCallback, useMemo, useRef, useState } from "react";
import { useDispatch } from "react-redux";

import { styles } from "../styles/common";
import { useCompactLayout } from "../utils/useBreakpoints";
import { formatError } from "../utils/errors";
import { downloadCsvExport, downloadJsonExport } from "../api";
import { importEntries, importEntriesDryRun } from "../store/entriesSlice";

function ImportDialog({
  file,
  summary,
  loading,
  confirming,
  onRevalidate,
  onConfirm,
  onReset,
  onClose,
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
        zIndex: 20,
      }}
      role="dialog"
      aria-modal="true"
    >
      <div
        style={{
          backgroundColor: "#1f2126",
          border: "1px solid #3a3d45",
          borderRadius: "0.6rem",
          padding: "1rem",
          maxWidth: "32rem",
          width: "100%",
          color: "#e6e6e6",
          boxShadow: "0 12px 40px rgba(0,0,0,0.4)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "1.05rem", fontWeight: 600 }}>Import CSV</div>
            <div style={{ ...styles.textMuted, fontSize: "0.9rem" }}>
              Dry-run already completed. Review and confirm.
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ ...styles.button, backgroundColor: "#444" }}
          >
            Close
          </button>
        </div>

        {file && (
          <div style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>
            Selected: <strong>{file.name}</strong> ({Math.max(1, Math.round(file.size / 1024))} kB)
          </div>
        )}

        {summary && (
          <div
            style={{
              backgroundColor: "#1a1c20",
              border: "1px solid #2f3244",
              borderRadius: "0.5rem",
              padding: "0.75rem",
              marginTop: "0.5rem",
            }}
          >
            <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.9rem" }}>
              <span>Created: {summary.created ?? 0}</span>
              <span>Updated: {summary.updated ?? 0}</span>
              <span>Skipped: {summary.skipped ?? 0}</span>
            </div>
            {Array.isArray(summary.details) && summary.details.length > 0 && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#d3d6de" }}>
                {summary.details.slice(0, 5).map((detail, idx) => (
                  <div key={idx} style={{ padding: "0.2rem 0" }}>
                    #{detail.row ?? "?"}: {detail.status}
                    {detail.reason ? ` · ${detail.reason}` : ""}
                    {detail.activity ? ` · ${detail.activity}` : ""}
                  </div>
                ))}
                {summary.details.length > 5 && (
                  <div style={{ opacity: 0.7 }}>
                    …and {summary.details.length - 5} more rows.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={onRevalidate}
            style={{ ...styles.button, backgroundColor: "#2a2f4f", opacity: loading ? 0.7 : 1 }}
            disabled={loading || confirming}
          >
            {loading ? "Validating…" : "Re-run dry-run"}
          </button>
          <button
            type="button"
            onClick={onReset}
            style={{ ...styles.button, backgroundColor: "#444" }}
            disabled={loading || confirming}
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{ ...styles.button, backgroundColor: "#2f9e44", opacity: confirming ? 0.7 : 1 }}
            disabled={confirming || loading || !summary}
          >
            {confirming ? "Importing…" : "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ImportExportPanel({ onNotify }) {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  const { isCompact } = useCompactLayout();
  const [exportingFormat, setExportingFormat] = useState(null);
  const [showDialog, setShowDialog] = useState(false);
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [validating, setValidating] = useState(false);
  const [confirming, setConfirming] = useState(false);

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

  const validateFile = (candidate) => {
    if (!candidate) return false;
    const name = candidate.name?.toLowerCase() || "";
    if (!name.endsWith(".csv")) {
      onNotify?.("Please select a CSV file (.csv).", "error");
      return false;
    }
    if (candidate.size === 0) {
      onNotify?.("Selected CSV file is empty.", "error");
      return false;
    }
    return true;
  };

  const runDryRun = useCallback(
    async (selected) => {
      setValidating(true);
      try {
        const response = await dispatch(importEntriesDryRun(selected)).unwrap();
        const summaryPayload = response?.summary || response;
        setSummary(summaryPayload || {});
        const { created = 0, updated = 0, skipped = 0 } = summaryPayload || {};
        onNotify?.(
          `Validation complete (${created} created, ${updated} updated, ${skipped} skipped)`,
          "success"
        );
      } catch (err) {
        setSummary(null);
        onNotify?.(`Dry-run failed: ${formatError(err)}`, "error");
      } finally {
        setValidating(false);
      }
    },
    [dispatch, onNotify]
  );

  const handleFileChange = useCallback(
    async (event) => {
      const selected = event.target.files?.[0];
      if (!selected) return;
      if (!validateFile(selected)) {
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }
      setFile(selected);
      setShowDialog(true);
      await runDryRun(selected);
    },
    [runDryRun]
  );

  const handleConfirm = useCallback(async () => {
    if (!file) return;
    setConfirming(true);
    try {
      const result = await dispatch(importEntries(file)).unwrap();
      const s = result?.summary || {};
      onNotify?.(
        `Import completed (${s.created ?? 0} created, ${s.updated ?? 0} updated, ${s.skipped ?? 0} skipped)`,
        "success"
      );
      setShowDialog(false);
      setFile(null);
      setSummary(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      onNotify?.(`Import failed: ${formatError(err)}`, "error");
    } finally {
      setConfirming(false);
    }
  }, [dispatch, file, onNotify]);

  const handleReset = useCallback(() => {
    setSummary(null);
    setFile(null);
    setShowDialog(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

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
    <>
      <input
        type="file"
        accept=".csv,text/csv"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <div style={containerStyle}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Entries data tools</h3>
          <span style={{ ...styles.textMuted, fontSize: "0.85rem" }}>
            Import CSV with automatic validation, or export CSV/JSON.
          </span>
        </div>
        <div style={actionRowStyle}>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            style={{
              ...styles.button,
              backgroundColor: "#29442f",
            }}
          >
            Import CSV
          </button>
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
      {showDialog && (
        <ImportDialog
          file={file}
          summary={summary}
          loading={validating}
          confirming={confirming}
          onRevalidate={() => file && runDryRun(file)}
          onConfirm={handleConfirm}
          onReset={handleReset}
          onClose={handleReset}
        />
      )}
    </>
  );
}
